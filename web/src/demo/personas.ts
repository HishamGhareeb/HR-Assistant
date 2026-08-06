/**
 * Mirrors glue/demo_seed.py's DEMO_TENANT_ID / DEMO_PERSONAS exactly --
 * these are convenience shortcuts for the sign-in screen, not a separate
 * source of truth. Run `python scripts/seed_demo_org.py` once against
 * your local Onyx/OpenFGA before these personas will see any real data.
 */

export const DEMO_TENANT_ID = "demo-org";

export interface DemoPersona {
  userId: string;
  displayName: string;
  department: string;
  roleDescription: string;
}

export const DEMO_PERSONAS: DemoPersona[] = [
  {
    userId: "priya",
    displayName: "Priya Nair",
    department: "Engineering",
    roleDescription: "Employee -- reports to Farah. Sees her own records and public policies.",
  },
  {
    userId: "noura",
    displayName: "Noura Al Khalifa",
    department: "Engineering",
    roleDescription: "Employee -- Bahraini team member with leave, appraisal, and payroll scenarios.",
  },
  {
    userId: "farah",
    displayName: "Farah Al Zayani",
    department: "Engineering",
    roleDescription: "Priya's manager -- sees her department's records, never salary data.",
  },
  {
    userId: "reem",
    displayName: "Reem Al Saffar",
    department: "Finance",
    roleDescription: "Finance manager -- useful for payroll and WPS walkthroughs.",
  },
  {
    userId: "hr-demo",
    displayName: "Demo HR Admin",
    department: "People Ops",
    roleDescription: "Full visibility -- suggestion inbox, admin console, and feedback dashboard.",
  },
];
