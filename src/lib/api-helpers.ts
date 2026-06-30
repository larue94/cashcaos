import { getServerSession } from 'next-auth'
import { authOptions } from './auth'
import { NextResponse } from 'next/server'
import { prisma } from './db'

export async function requireOrg() {
  const session = await getServerSession(authOptions)
  if (!session?.user?.email) {
    return { error: NextResponse.json({ error: 'Unauthorized' }, { status: 401 }), orgId: null }
  }
  const user = await prisma.user.findUnique({
    where: { email: session.user.email },
    select: { orgId: true },
  })
  if (!user?.orgId) {
    return { error: NextResponse.json({ error: 'No organization' }, { status: 403 }), orgId: null }
  }
  return { error: null, orgId: user.orgId }
}

export function ok<T>(data: T, status = 200) {
  return NextResponse.json(data, { status })
}

export function err(message: string, status = 400) {
  return NextResponse.json({ error: message }, { status })
}
