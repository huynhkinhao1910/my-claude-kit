# Workers on RabbitMQ, cache on Redis, outbound HTTP

## RabbitMQ with aio-pika

```bash
uv add aio-pika
```

### Publish after commit

Publish only after the DB transaction commits, otherwise a consumer can see a message for a row that was rolled back.

```python
class OrderEvents(Protocol):
    async def order_paid(self, order_id: int) -> None: ...


class RabbitOrderEvents:
    def __init__(self, channel: aio_pika.abc.AbstractChannel) -> None:
        self._channel = channel

    async def order_paid(self, order_id: int) -> None:
        body = json.dumps({"order_id": order_id, "event_id": uuid.uuid4().hex}).encode()
        await self._channel.default_exchange.publish(
            aio_pika.Message(body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT, content_type="application/json"),
            routing_key="orders.paid",
        )
```

Open the connection in `lifespan` (`aio_pika.connect_robust(settings.amqp_url)`), keep one channel in `app.state`, expose it through a dependency so tests can override it with an in-memory fake.

If losing an event is unacceptable, write it to an `outbox` table inside the same transaction and publish from a relay loop.

### Consumer (separate process)

```python
async def handle(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):  # ack on success, reject → DLX on exception
        payload = OrderPaid.model_validate_json(message.body)
        async with SessionFactory() as session, session.begin():
            if await ProcessedEvents(session).seen(payload.event_id):
                return  # idempotent: redelivery is normal
            await send_receipt(session, payload.order_id)
            await ProcessedEvents(session).mark(payload.event_id)


async def main() -> None:
    connection = await aio_pika.connect_robust(get_settings().amqp_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        queue = await channel.declare_queue(
            "orders.paid", durable=True, arguments={"x-dead-letter-exchange": "dlx"}
        )
        await queue.consume(handle)
        await asyncio.Future()  # run until cancelled
```

Rules:
- Consumers are idempotent (store processed `event_id`) because RabbitMQ delivers at least once.
- Validate the message body with a Pydantic model; a bad message goes to the DLX, not an infinite requeue.
- `prefetch_count` bounds in-flight work; long jobs get their own queue.
- Run workers as their own container/process (`python -m app.workers.orders`), never inside the web process.
- Heavy scheduled or retry-heavy workloads: consider Celery/Dramatiq on RabbitMQ only if the project already uses them.

## Redis cache (redis.asyncio)

```python
from redis.asyncio import Redis

redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1.0)


async def get_product(product_id: int, repo: ProductRepository) -> ProductOut:
    key = f"product:v1:{product_id}"
    if cached := await redis.get(key):
        return ProductOut.model_validate_json(cached)
    product = ProductOut.model_validate(await repo.get_or_fail(product_id))
    await redis.set(key, product.model_dump_json(), ex=300)
    return product
```

- Every key has a TTL and a version segment (`v1`) so a schema change does not read stale shapes.
- Invalidate on write in the service, after commit.
- A Redis outage degrades to the DB; it never becomes a 500. Catch `redis.RedisError`, log it, fall through.
- Locks: `redis.lock(name, timeout=10, blocking_timeout=2)`; always with a timeout. See `redis-patterns`.

## Outbound HTTP

- One `httpx.AsyncClient` per app (lifespan), with `timeout=httpx.Timeout(5.0, connect=2.0)` and `limits=httpx.Limits(max_connections=50)`.
- Wrap each third party in a small client class returning typed models; the service depends on its Protocol.
- Retries only for idempotent calls, with backoff and a cap (`tenacity` if already installed, otherwise a short loop).
- Log the request id and the third party's status/latency; never the auth header or full body.
