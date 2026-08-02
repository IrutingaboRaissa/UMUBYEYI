"use client";

import Link from "next/link";
import { useLanguage } from "@/lib/language";

export default function PrivacyContent() {
  const { lang } = useLanguage();

  if (lang === "rw") {
    return (
      <div className="legal-page">
        <Link href="/" className="legal-back">← Ahabanza · Home</Link>
        <h1>Politiki y&apos;Ibanga</h1>
        <div className="legal-updated">Yavuguruwe bwa nyuma: Nyakanga 26, 2026</div>

        <div className="legal-summary">
          <b>Muri make:</b> Umubyeyi ntibika amakuru yawe kuri seriveri. Ibiganiro byawe, uko
          wiyumva, ibizamini n&apos;amasuzuma bibikwa gusa kuri iyi terefone/mudasobwa yawe.
          Ubutumwa wandika mu kiganiro busohoka gusa ku murinzi w&apos;ubwenge bw&apos;ikoranabuhanga
          (Groq) kugira ngo bagusubize, kandi nta konti cyangwa amazina asabwa.
        </div>

        <p>
          Umubyeyi ni serivisi y&apos;ubuntu, ivuga Ikinyarwanda n&apos;Icyongereza, ari umushinga
          w&apos;ubushakashatsi bwa kaminuza wa Raissa Irutingabo (impamyabumenyi ya BSc muri
          Software Engineering, muri African Leadership University), utanga amakuru ku byerekeye
          imibereho myiza yo mu mutima n&apos;ibikoresho byo kwisuzuma ku babyeyi babyaye ubwa
          mbere. Ntabwo ari isosiyete cyangwa igicuruzwa cy&apos;ubucuruzi. Iyi politiki isobanura,
          mu buryo bwumvikana kandi nyabwo, ibyabaho ku makuru yawe igihe ukoresheje iyi
          porogaramu.
        </p>

        <h2>1. Ibyo Umubyeyi abika, n&apos;aho abibika</h2>
        <p>
          Ibyo Umubyeyi yibuka byose kuri wewe, birimo amateka y&apos;ibiganiro byawe, uko wiyumva
          wanditse, amateka y&apos;isuzuma ryoroheje, amanota y&apos;ikizamini cy&apos;imibereho
          EPDS-10, umubare w&apos;iminsi ukurikiranye mu kwisuzuma, ururimi wahisemo, na (niba
          wabishatse) umubare w&apos;ibanga (PIN) wo kurinda ibanga, bibikwa gusa kuri
          mudasobwa/terefone yawe bwite. Nta na kimwe muri ibi cyoherezwa cyangwa kigumana kuri
          seriveri iyo ari yo yose ikoreshwa n&apos;uyu mushinga.
        </p>
        <ul>
          <li>Niba washyizeho PIN yo kurinda ibanga, hibikwa gusa umubare w&apos;igenzura (hash)
            wayo; PIN ubwayo ntibigera ibikwa cyangwa ikoherezwa ahandi hose, harimo no kuri
            twe.</li>
          <li>Nta na kimwe muri ibi gisaba konti, amazina, aderesi email, cyangwa nimero ya
            terefone.</li>
          <li>Gusiba amakuru ya porogaramu kuri mudasobwa yawe, kongera gushyiraho porogaramu
            yawe y&apos;urubuga (browser), cyangwa gukoresha uburyo bwo muri porogaramu
            &quot;Wibagiwe PIN → Siba byose&quot; bisiba burundu aya makuru. Nta bwikorezi
            (backup) buri kuri seriveri, bityo ntibishobora kongera kubonwa nyuma.</li>
        </ul>

        <h2>2. Ibyo tutakusanya</h2>
        <ul>
          <li>Nta konti, kwiyandikisha, cyangwa kwinjira mu buryo ubwo aribwo bwose.</li>
          <li>Nta &quot;cookies.&quot;</li>
          <li>Nta gakoresho ko gukurikirana cyangwa &quot;analytics&quot; ubwo ari bwo bwose.</li>
          <li>Nta bubiko bw&apos;amakuru kuri seriveri. Ibisubizo ku butumwa wandika bikorwa
            kandi bikagarurwa kuri mudasobwa yawe bidasize aho bibitswe n&apos;uyu mushinga.</li>
        </ul>

        <h2>3. Ibyo bisohoka kuri mudasobwa yawe, n&apos;impamvu</h2>
        <p>
          Ikintu kimwe gisohoka kuri mudasobwa yawe ni umwandiko w&apos;ubutumwa bwawe bwo mu
          kiganiro, woherezwa ku rubuga rw&apos;ubwenge bw&apos;ubukorano (
          <a href="https://groq.com" target="_blank" rel="noopener noreferrer">Groq</a>) kugira ngo
          rukubwize igisubizo. Kugira ngo ibibazo bikurikirana bisobanuke, hafi iby&apos;ibiganiro
          byinshi biheruka biva mu kiganiro cyawe cy&apos;ubu bishobora koherezwa hamwe
          n&apos;ubutumwa bushya bwawe. Ibindi bikorwa bibiri bike ku byago, ni ukuvuga igisubizo cyo
          kuramukanya n&apos;imitwe y&apos;ibiganiro ikorwa mu buryo bwikora, na byo bikoresha uru
          rubuga rumwe, byohereza gusa umwandiko mugufi ukenewe kuri icyo gikorwa.
        </p>
        <p>
          Uyu mushinga ntugenzura uko Groq ubwayo ikoresha amakuru iyakira; ushobora gusoma{" "}
          <a href="https://groq.com/privacy-policy/" target="_blank" rel="noopener noreferrer">
            politiki y&apos;ibanga ya Groq ubwayo
          </a>{" "}
          kugira ngo umenye uko bimeze ku ruhande rwabo. Niba Groq idakora, Umubyeyi yisubira ku
          gisubizo cyakorewe kuri mudasobwa cyangwa umwandiko wateguwe mbere, bityo kubona
          igisubizo ntibiterwa n&apos;uko iri hererekanya ry&apos;amakuru ryabaye.
        </p>

        <h2>4. Ikoranabuhanga rikoreshwa mu gushyira porogaramu ku rubuga</h2>
        <p>
          Umubyeyi ishyirwa ku rubuga rwa Vercel (na, ku bushake, kuri serivisi ya Render ku
          bijyanye na porogaramu ya Python). Nk&apos;uko bimeze ku yandi masite yose, aba
          bakoresha iyi serivisi bashobora kubona amakuru asanzwe agenda mu rusobe (nk&apos;aderesi
          ya IP yawe) nk&apos;uko bisanzwe bigenda ku rubuga urwo arirwo rwose. Ibi ni ibisanzwe ku
          bijyanye n&apos;ikoranabuhanga ry&apos;ibanze, ntabwo ari ikintu porogaramu y&apos;uyu
          mushinga ubwayo isoma, yandika, cyangwa ibika.
        </p>

        <h2>5. Uko ikaga n&apos;umutekano bicungwa</h2>
        <p>
          Ubutumwa bumwe na bumwe (urugero, ubuvuga ku kwigirira nabi cyangwa ikaga
          ry&apos;ubuzima) bumenyekana hifashishijwe amabwiriza ahamye, akorera mu buryo
          bw&apos;ikoranabuhanga bugenwe mbere ari muri porogaramu ubwayo, ntabwo ari serivisi
          y&apos;hanze, kandi bisubizwamo ubutumwa bwo kuboneza ku bufasha bw&apos;ihutirwa
          (nimero y&apos;ihutirwa yo mu Rwanda, 114) hamwe n&apos;ubutumwa bwo gufasha mu kaga. Ubu
          bumenyekane ntibuterwa, cyangwa ngo bwoherezwe, ku wundi muntu cyangwa serivisi iyo ari
          yo yose.
        </p>

        <h2>6. Ikizamini cy&apos;imibereho EPDS-10 n&apos;isuzuma ryoroheje</h2>
        <p>
          Isuzuma ryoroheje n&apos;ikizamini cy&apos;imibereho EPDS-10 byombi ni ibikoresho byo
          kwisuzuma wenyine, ntabwo ari isuzuma ry&apos;ubuvuzi, kandi nta na kimwe muri byo
          kibika ibisubizo byawe kuri buri kibazo ku giti cyacyo; ni igisubizo rusange gusa (na,
          ku bushake, itariki/amanota wahisemo kubika kugira ngo ubone uko ugenda) ni cyo gibikwa
          kuri mudasobwa yawe. Amagambo y&apos;Ikinyarwanda y&apos;ibibazo bya EPDS-10 ni
          ibisobanuro by&apos;uyu mushinga ubwawo kandi ntibyigeze binyuzwa mu maso h&apos;umuganga
          cyangwa umusemuzi w&apos;Ikinyarwanda nk&apos;ururimi yavukiyemo; reba ibisobanuro biri
          muri porogaramu kuri iyo paji kugira ngo umenye byinshi.
        </p>

        <h2>7. Abana</h2>
        <p>
          Umubyeyi ntabwo yagenewe, cyangwa ngo ikoreshwe n&apos;abana. Isuzuma ryoroheje risaba
          imyaka iri hagati ya 18 na 60.
        </p>

        <h2>8. Impinduka kuri iyi politiki</h2>
        <p>
          Iyi politiki nimba ihindutse, itariki yo &quot;kuvugururwa bwa nyuma&quot; hejuru na yo
          izahinduka. Kubera ko uyu ari umushinga w&apos;ubushakashatsi bwa kaminuza aho kuba
          serivisi y&apos;ubucuruzi, impinduka zitegerejwe kuba ivugurura ry&apos;inyandiko rimwe
          na rimwe, ntabwo ari uburyo bwo kumenyesha no kwemeza.
        </p>

        <h2>9. Aho twavugana</h2>
        <p>
          Umubyeyi ni umushinga w&apos;ubushakashatsi bwa kaminuza wa Raissa Irutingabo
          (impamyabumenyi ya BSc muri Software Engineering, muri African Leadership University).
          Ibibazo ku byerekeye iyi politiki cyangwa uyu mushinga birashobora kuvugwa binyuze kuri
          {" "}
          <a href="https://github.com/IrutingaboRaissa/UMUBYEYI" target="_blank" rel="noopener noreferrer">
            urubuga rwa GitHub rw&apos;uyu mushinga
          </a>.
        </p>

        <div className="legal-footer-links">
          <Link href="/eula" className="btn btn-sm">Amasezerano y&apos;Ukoresha</Link>
          <Link href="/" className="btn btn-sm">← Garuka kuri Umubyeyi</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="legal-page">
      <Link href="/" className="legal-back">← Home</Link>
      <h1>Privacy Policy</h1>
      <div className="legal-updated">Last updated: July 26, 2026</div>

      <div className="legal-summary">
        <b>In short:</b> Umubyeyi doesn&apos;t store your data on a server. Your chats, moods, and
        test results stay only on this device. Your chat messages are sent to an external AI
        provider (Groq) so it can generate a reply. That&apos;s the only place your words leave
        your device. There are no accounts and no names required.
      </div>

      <p>
        Umubyeyi is a free, bilingual (Kinyarwanda/English) academic capstone project by Raissa
        Irutingabo (BSc Software Engineering, African Leadership University), providing emotional
        wellbeing information and self-assessment tools for first-time mothers. It is not a
        company or a commercial product. This policy explains, as plainly and accurately as
        possible, what happens to your information when you use it.
      </p>

      <h2>1. What Umubyeyi stores, and where</h2>
      <p>
        Everything Umubyeyi remembers about you, including your chat history, mood check-ins, guided
        screening check-in history, EPDS-10 wellness-test scores, your check-in streak, your
        language preference, and (if you set one) a privacy-lock PIN, is stored only in your
        browser&apos;s local storage, on your own device. None of it is sent to, or kept on, any
        server operated by this project.
      </p>
      <ul>
        <li>If you set a privacy-lock PIN, only its one-way cryptographic hash is stored; the
          PIN itself is never saved or transmitted anywhere, including to us.</li>
        <li>Nothing here requires an account, a name, an email address, or a phone number.</li>
        <li>Clearing your browser&apos;s site data, resetting your browser profile, or using the
          in-app &quot;Forgot PIN → Reset everything&quot; option permanently deletes this local
          data. There is no server-side backup, so it cannot be recovered afterward.</li>
      </ul>

      <h2>2. What we do not collect</h2>
      <ul>
        <li>No accounts, sign-up, or login of any kind.</li>
        <li>No cookies.</li>
        <li>No analytics or tracking scripts of any kind.</li>
        <li>No server-side database. Responses to your messages are generated and returned to
          your browser without being logged or stored by this project afterward.</li>
      </ul>

      <h2>3. What leaves your device, and why</h2>
      <p>
        The one thing that does leave your device is the text of your chat messages, sent to a
        third-party AI service (<a href="https://groq.com" target="_blank" rel="noopener noreferrer">Groq</a>)
        so it can generate a reply. To keep follow-up questions coherent, up to the last several
        turns of your current conversation are sent along with each new message. Two lower-stakes
        features (greeting responses and automatically generated chat titles) also use this
        same service, sending only the short text relevant to that feature.
      </p>
      <p>
        This project doesn&apos;t control how Groq itself handles the data it receives; you can
        review{" "}
        <a href="https://groq.com/privacy-policy/" target="_blank" rel="noopener noreferrer">
          Groq&apos;s own privacy policy
        </a>{" "}
        for details on their side. If Groq is unavailable, Umubyeyi automatically falls back to a
        locally-run response or a pre-written passage, so getting a reply doesn&apos;t depend on
        this exchange happening.
      </p>

      <h2>4. Hosting infrastructure</h2>
      <p>
        Umubyeyi is hosted on Vercel (and, optionally for its Python backend, Render). As with any
        website, these hosting providers may see standard connection information, such as your IP
        address, as part of normal web traffic handling. This is infrastructure-level behavior
        common to all websites, not something this project&apos;s own code reads, logs, or stores.
      </p>

      <h2>5. Crisis and safety handling</h2>
      <p>
        Certain messages (for example, ones mentioning self-harm or a medical emergency) are
        detected using fixed, deterministic rules running entirely within the app (not by any
        external service) and are answered with a direct referral to emergency help (Rwanda&apos;s
        emergency line, 114) and a crisis-support message. This detection does not depend on, or
        get sent to, any third party.
      </p>

      <h2>6. The EPDS-10 wellness test and guided check-in</h2>
      <p>
        The guided screening check-in and the EPDS-10 wellness test are self-assessment tools, not
        medical diagnoses, and neither stores your individual question-by-question answers; only
        a summary result (and, optionally, a date/score you choose to save to see your own trend)
        stays on your device. The Kinyarwanda wording of the EPDS-10 questions is this project&apos;s
        own translation and has not been reviewed by a clinician or a native Kinyarwanda-speaking
        translator; see the in-app disclaimer on that page for details.
      </p>

      <h2>7. Children</h2>
      <p>
        Umubyeyi is not directed at, or intended for use by, children. The guided check-in
        requires a stated age between 18 and 60.
      </p>

      <h2>8. Changes to this policy</h2>
      <p>
        If this policy changes, the &quot;last updated&quot; date above will change too. Since this
        is a capstone research project rather than a commercial service, changes are expected to
        be occasional documentation updates, not a notice-and-consent process.
      </p>

      <h2>9. Contact</h2>
      <p>
        Umubyeyi is an academic capstone project by Raissa Irutingabo (BSc Software Engineering,
        African Leadership University). Questions about this policy or the project can be raised
        via the{" "}
        <a href="https://github.com/IrutingaboRaissa/UMUBYEYI" target="_blank" rel="noopener noreferrer">
          project&apos;s GitHub repository
        </a>.
      </p>

      <div className="legal-footer-links">
        <Link href="/eula" className="btn btn-sm">End User License Agreement</Link>
        <Link href="/" className="btn btn-sm">← Back to Umubyeyi</Link>
      </div>
    </div>
  );
}
