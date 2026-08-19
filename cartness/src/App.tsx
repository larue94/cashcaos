import { useCallback, useState } from "react";
import { Nav, Hero, Problem, HowItWorks } from "./components/sections/Top";
import {
  DemoMoment,
  Benefits,
  Pricing,
  FAQ,
  FinalCTA,
  Footer,
} from "./components/sections/Bottom";
import { LeadModal, type ModalRequest } from "./components/LeadModal";

export default function App() {
  const [modal, setModal] = useState<ModalRequest>(null);

  const openModal = useCallback((request: NonNullable<ModalRequest>) => {
    setModal(request);
  }, []);

  const closeModal = useCallback(() => setModal(null), []);

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <Nav onOpen={openModal} />

      <main id="main">
        <Hero />
        <Problem />
        <HowItWorks />
        <DemoMoment />
        <Benefits />
        <Pricing onOpen={openModal} />
        <FAQ />
        <FinalCTA />
      </main>

      <Footer />

      <LeadModal request={modal} onClose={closeModal} />
    </>
  );
}
