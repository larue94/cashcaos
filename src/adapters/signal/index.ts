import type { SignalProvider } from '@/types/integrations'
import { ManualSignalAdapter } from './manual'

export function getSignalProvider(): SignalProvider {
  return new ManualSignalAdapter()
}
