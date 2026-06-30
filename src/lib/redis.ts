import { Redis } from 'ioredis'

const globalForRedis = globalThis as unknown as { redis: Redis }

function createRedis() {
  const url = process.env.REDIS_URL || 'redis://localhost:6379'
  const client = new Redis(url, { maxRetriesPerRequest: null, lazyConnect: true })
  client.on('error', (err) => {
    if (process.env.NODE_ENV !== 'test') console.error('[Redis]', err.message)
  })
  return client
}

export const redis = globalForRedis.redis || createRedis()
if (process.env.NODE_ENV !== 'production') globalForRedis.redis = redis
