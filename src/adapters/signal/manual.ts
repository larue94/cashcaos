import type { SignalProvider, IntentSignal } from '@/types/integrations'
import { prisma } from '@/lib/db'

// Returns signals already stored in DB for a lead (manual tags + webhook ingests)
export class ManualSignalAdapter implements SignalProvider {
  name = 'manual'

  async fetchSignals(leadId: string): Promise<IntentSignal[]> {
    const signals = await prisma.signal.findMany({
      where: { leadId },
      orderBy: { occurredAt: 'desc' },
    })
    return signals.map((s: { type: string; source: string; payload: unknown; weight: number; occurredAt: Date }) => ({
      type:       s.type,
      source:     s.source,
      payload:    s.payload as Record<string, unknown>,
      weight:     s.weight,
      occurredAt: s.occurredAt,
    }))
  }
}
