import { NextAuthOptions } from 'next-auth'
import { PrismaAdapter } from '@next-auth/prisma-adapter'
import EmailProvider from 'next-auth/providers/email'
import GoogleProvider from 'next-auth/providers/google'
import { prisma } from './db'

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  providers: [
    EmailProvider({
      server: {
        host: process.env.EMAIL_SERVER_HOST || 'smtp.gmail.com',
        port: Number(process.env.EMAIL_SERVER_PORT) || 587,
        auth: {
          user: process.env.EMAIL_SERVER_USER || '',
          pass: process.env.EMAIL_SERVER_PASSWORD || '',
        },
      },
      from: process.env.EMAIL_FROM || 'noreply@gojiberry.local',
    }),
    ...(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET
      ? [
          GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
          }),
        ]
      : []),
  ],
  session: { strategy: 'database' },
  pages: {
    signIn: '/auth/signin',
    verifyRequest: '/auth/verify',
  },
  callbacks: {
    async session({ session, user }) {
      if (session.user) {
        ;(session.user as typeof session.user & { id: string }).id = user.id
        // attach org
        const dbUser = await prisma.user.findUnique({
          where: { id: user.id },
          select: { orgId: true },
        })
        ;(session.user as typeof session.user & { orgId?: string | null }).orgId =
          dbUser?.orgId ?? null
      }
      return session
    },
  },
  events: {
    async createUser({ user }) {
      // Auto-create an org for new users
      const org = await prisma.organization.create({
        data: { name: user.name || user.email || 'My Org' },
      })
      await prisma.user.update({ where: { id: user.id }, data: { orgId: org.id } })
    },
  },
}
