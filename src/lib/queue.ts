import { Queue, Worker, Job } from 'bullmq'
import { redis } from './redis'

export const QUEUE_SEQUENCE = 'sequence-steps'
export const QUEUE_SIGNALS  = 'signal-poll'
export const QUEUE_SCORE    = 'lead-score'
export const QUEUE_ENRICH   = 'lead-enrich'

const connection = { host: '127.0.0.1', port: 6379 }

function makeQueue(name: string) {
  return new Queue(name, {
    connection,
    defaultJobOptions: { removeOnComplete: 100, removeOnFail: 200 },
  })
}

export const sequenceQueue = makeQueue(QUEUE_SEQUENCE)
export const signalQueue   = makeQueue(QUEUE_SIGNALS)
export const scoreQueue    = makeQueue(QUEUE_SCORE)
export const enrichQueue   = makeQueue(QUEUE_ENRICH)

// Job payload shapes
export type SequenceJobData = {
  enrollmentId: string
  stepIndex: number
  leadId: string
  campaignId: string
}

export type ScoreJobData   = { leadId: string }
export type EnrichJobData  = { leadId: string }
