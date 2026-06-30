import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  console.log('Seeding…')

  // Create demo org + user
  const org = await prisma.organization.upsert({
    where:  { id: 'demo-org' },
    create: { id: 'demo-org', name: 'Demo Org' },
    update: {},
  })

  const user = await prisma.user.upsert({
    where:  { email: 'demo@gojiberry.local' },
    create: { email: 'demo@gojiberry.local', name: 'Demo User', orgId: org.id },
    update: {},
  })

  // ICP
  const icp = await prisma.icpProfile.upsert({
    where:  { id: 'demo-icp' },
    create: {
      id:               'demo-icp',
      orgId:            org.id,
      name:             'B2B SaaS ICP',
      description:      'We sell AI-powered outbound sales automation to B2B SaaS companies. Our buyers are VP of Sales, Head of Growth, and founders at Series A–C companies with 20–500 employees.',
      targetTitles:     ['VP of Sales', 'Head of Growth', 'Founder', 'CEO', 'Head of Revenue'],
      targetIndustries: ['Software', 'SaaS', 'Technology', 'FinTech'],
      companySizeMin:   20,
      companySizeMax:   500,
      keywords:         ['outbound', 'sales automation', 'lead generation', 'B2B', 'pipeline'],
      scoringWeights:   { fit: 60, intent: 40 },
    },
    update: {},
  })

  // Sample leads
  const leadsData = [
    { firstName: 'Alice', lastName: 'Chen',     email: 'alice@saasco.io',    title: 'VP of Sales',    company: 'SaaSCo',        industry: 'Software', companySize: '51-200' },
    { firstName: 'Bob',   lastName: 'Martinez',  email: 'bob@growthly.com',   title: 'Head of Growth', company: 'Growthly',       industry: 'SaaS',     companySize: '11-50' },
    { firstName: 'Carol', lastName: 'Smith',     email: 'carol@techstartup.io',title: 'CEO',           company: 'TechStartup',    industry: 'Technology', companySize: '11-50' },
    { firstName: 'Dave',  lastName: 'Johnson',   email: 'dave@oldcorp.com',   title: 'IT Manager',     company: 'OldCorp',        industry: 'Manufacturing', companySize: '5001-10000' },
    { firstName: 'Eve',   lastName: 'Williams',  email: 'eve@fintechpro.com', title: 'Head of Revenue', company: 'FintechPro',   industry: 'FinTech',  companySize: '51-200' },
  ]

  for (const l of leadsData) {
    const lead = await prisma.lead.upsert({
      where:  { id: `demo-${l.email}` },
      create: { id: `demo-${l.email}`, orgId: org.id, source: 'seed', ...l },
      update: {},
    })

    // Add some signals
    if (l.title.includes('VP') || l.title.includes('Head') || l.title === 'CEO') {
      await prisma.signal.upsert({
        where:  { id: `sig-${lead.id}-1` },
        create: {
          id:       `sig-${lead.id}-1`,
          leadId:   lead.id,
          type:     'website_visit',
          source:   'seed',
          payload:  { page: '/pricing' },
          weight:   1.5,
        },
        update: {},
      })
    }
  }

  console.log('Seed complete.')
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
