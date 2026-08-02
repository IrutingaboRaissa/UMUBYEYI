"use client";

import Link from "next/link";
import { useLanguage } from "@/lib/language";

export default function EulaContent() {
  const { lang } = useLanguage();

  if (lang === "rw") {
    return (
      <div className="legal-page">
        <Link href="/" className="legal-back">← Ahabanza · Home</Link>
        <h1>Amasezerano y&apos;Ukoresha</h1>
        <div className="legal-updated">Yavuguruwe bwa nyuma: Nyakanga 26, 2026</div>

        <div className="legal-summary">
          <b>Muri make:</b> Umubyeyi ni umushinga w&apos;ubushakashatsi, si serivisi
          y&apos;ubuvuzi. Ntisimbura umuganga cyangwa ubufasha bw&apos;ihutirwa. Niba uri mu kaga,
          hamagara 114 cyangwa ujye ku ivuriro ryegereye ako kanya.
        </div>

        <p>
          Umubyeyi ni serivisi y&apos;ubuntu, itari iy&apos;ubucuruzi, umushinga
          w&apos;ubushakashatsi bwa kaminuza (impamyabumenyi ya BSc muri Software Engineering,
          muri African Leadership University) utanga amakuru avuga Ikinyarwanda n&apos;Icyongereza
          ku byerekeye imibereho myiza yo mu mutima, isuzuma ryoroheje, hamwe n&apos;ikizamini
          cy&apos;imibereho EPDS-10 ku babyeyi babyaye ubwa mbere. Ukoresheje Umubyeyi, wemeranya
          n&apos;amategeko akurikira.
        </p>

        <h2>1. Ntabwo ari ubuvuzi</h2>
        <p>
          Umubyeyi itanga amakuru rusange yo kwigisha no gufasha mu mutima gusa. Ntabwo ari
          ubufasha bw&apos;ihutirwa, inama y&apos;ubuvuzi, isuzuma ry&apos;indwara, cyangwa
          kuvura, kandi gukoresha iyi porogaramu ntibirema umubano w&apos;umuganga n&apos;umurwayi
          cyangwa uwundi mubano w&apos;ubuvuzi uwo ari wo wose. Isuzuma ryoroheje n&apos;ikizamini
          EPDS-10 birebera niba ibisubizo byawe bisa n&apos;ibiteganijwe mu bushakashatsi;
          ntibisuzuma indwara yo kwiheba nyuma yo kubyara cyangwa indwara iyo ari yo yose. Niba
          uri mu kaga cyangwa mu bibazo bikomeye, hamagara nimero y&apos;ihutirwa yo mu Rwanda
          (114) cyangwa ujye ku ivuriro ryegereye ako kanya aho kwiringira kuri iyi porogaramu.
        </p>

        <h2>2. Imbogamizi z&apos;umushinga w&apos;ubushakashatsi</h2>
        <p>Wemeye kandi wumva ko Umubyeyi ari umushinga w&apos;ubushakashatsi, ntabwo ari igicuruzwa cy&apos;ubuvuzi cyemejwe:</p>
        <ul>
          <li>Icyitegererezo cyo kwisuzuma cyize ku bipimo by&apos;abagenzurwa babyaye vuba biva
            mu gihugu cya Bangladesh, ntabwo ari u Rwanda, kandi ukuri kwacyo ku baturage
            b&apos;u Rwanda ntibwigeze bugenzurwa ukwiye.</li>
          <li>Amagambo y&apos;Ikinyarwanda akoreshwa muri porogaramu yose, harimo n&apos;ikizamini
            cy&apos;imibereho EPDS-10, ni ibisobanuro by&apos;uyu mushinga kandi ntibyigeze
            binyuzwa mu maso h&apos;umuganga cyangwa umusemuzi w&apos;ururimi kavukire.</li>
          <li>Ibisubizo bikorwa n&apos;igikorwa cyo kuganira (haba biva ku rubuga rw&apos;hanze
            rw&apos;ubwenge bw&apos;ubukorano cyangwa icyitegererezo cy&apos;uyu mushinga
            cyihariye) bikorwa mu buryo bwikora kandi rimwe na rimwe bishobora kuba bitujuje,
            bitagaragaza neza, cyangwa bikabura urujijo; ntibisuzumwa n&apos;umuntu mbere yo
            kukwereka.</li>
        </ul>

        <h2>3. Kwemererwa gukoresha</h2>
        <p>
          Umubyeyi yagenewe abakuze kandi ntabwo yagenewe abana. Isuzuma ryoroheje risaba imyaka
          iri hagati ya 18 na 60.
        </p>

        <h2>4. Ukoresha gukwiye</h2>
        <p>
          Wemeranya gukoresha Umubyeyi gusa ku ntego yayo, ni ukuvuga ubufasha bw&apos;amakuru no mu
          mutima, bwite kandi butari ubucuruzi, kandi ntugerageze guhungabanya, gusesengura ngo
          ubone uko wabangamira, cyangwa gukoresha nabi iyi serivisi mu buryo bwabangamira
          ababikoresha bandi.
        </p>

        <h2>5. Serivisi z&apos;hanze</h2>
        <p>
          Igikorwa cyo kuganira cya Umubyeyi cyohereza ubutumwa bwawe ku rubuga rw&apos;hanze
          rw&apos;ubwenge bw&apos;ubukorano (Groq) kugira ngo rutange ibisubizo, nk&apos;uko
          bisobanuwe muri{" "}
          <Link href="/privacy">Politiki y&apos;Ibanga</Link>. Gukoresha kwawe igikorwa cyo
          kuganira cya Umubyeyi na byo bigengwa n&apos;amategeko ya urwo rubuga ubwarwo.
        </p>

        <h2>6. Nta bwishingizi</h2>
        <p>
          Umubyeyi itangwa &quot;uko yakabaye&quot; kandi &quot;uko ihari,&quot; nta bwishingizi
          ubwo ari bwo bwose, ku mugaragaro cyangwa mu buryo butagaragara, harimo ku byerekeye
          ukuri, kwizerwa, cyangwa kuboneza ku ntego runaka. Kubera ko ari umushinga wa kaminuza,
          ntabwo itangwa n&apos;ubwishingizi bw&apos;ubucuruzi ku byerekeye ko izahora ikora,
          ubufasha, cyangwa ukuri.
        </p>

        <h2>7. Kugarukira ku birego</h2>
        <p>
          Ku rugero rwemewe n&apos;amategeko akurikizwa, umwanditsi ntabwo ashobora kubazwa
          ibyago, kubura, cyangwa igihombo icyo aricyo cyose kiturutse ku gukoresha kwawe, cyangwa
          kutabasha gukoresha, Umubyeyi, harimo no kwiringira ku gisubizo cy&apos;isuzuma icyo
          aricyo cyose, igisubizo cyo mu kiganiro, cyangwa igisubizo cy&apos;ikizamini
          wisuzumye wenyine. Umubyeyi ntabwo isimbura ubufasha bw&apos;ubuvuzi cyangwa
          ubw&apos;imibereho myiza yo mu mutima buhabwa n&apos;inzobere.
        </p>

        <h2>8. Uburenganzira ku mutungo w&apos;ubwenge</h2>
        <p>
          Porogaramu, ibikubiyemo, n&apos;imiterere bya Umubyeyi ni umurimo w&apos;umwanditsi
          wabyo, byakozwe ku mushinga wa kaminuza, kandi bitangwa hakurikijwe amategeko
          y&apos;ububiko bwa GitHub bw&apos;uyu mushinga. Bimwe mu bipimo n&apos;ibyitegererezo
          byakoreshejwe mu kwigisha ibikorwa byo kwisuzuma no gutanga ibisubizo bya Umubyeyi
          bifite amategeko yabyo yihariye (urugero, ibipimo by&apos;indwara yo kwiheba nyuma yo
          kubyara biboneka kuri Mendeley, byemerewe na CC BY 4.0); reba inyandiko z&apos;ububiko
          bw&apos;uyu mushinga kugira ngo ubone amakuru yose.
        </p>

        <h2>9. Amakuru abitswe kuri mudasobwa n&apos;irangiza</h2>
        <p>
          Ushobora guhagarika gukoresha Umubyeyi igihe icyo aricyo cyose. Kubera ko amakuru yawe
          yose abitswe kuri mudasobwa yawe bwite, ushobora kuyasiba wenyine igihe icyo aricyo cyose
          usibye amakuru y&apos;urubuga kuri porogaramu yawe cyangwa ukoresheje uburyo bwo muri
          porogaramu &quot;Wibagiwe PIN → Siba byose&quot;; nta konti igomba gufungwa kandi nta
          bwikorezi (backup) buri kuri seriveri bugomba gusibwa.
        </p>

        <h2>10. Impinduka kuri aya masezerano</h2>
        <p>
          Aya masezerano ashobora kuvugururwa uko umushinga ugenda utera imbere. Gukomeza
          gukoresha Umubyeyi nyuma y&apos;ivugurura bisobanuye ko wemeye amategeko avuguruye.
        </p>

        <h2>11. Imiterere y&apos;amategeko</h2>
        <p>
          Umubyeyi ni umushinga w&apos;ubushakashatsi bwa kaminuza, ntabwo ari urwego
          rw&apos;amategeko rw&apos;ubucuruzi. Aya masezerano atangwa mu kwizerana kugira ngo
          agaragaze icyo abakoresha bagomba kwitega, aho kuba ikimenyetso cy&apos;inama
          z&apos;amategeko z&apos;umwuga.
        </p>

        <div className="legal-footer-links">
          <Link href="/privacy" className="btn btn-sm">Politiki y&apos;Ibanga</Link>
          <Link href="/" className="btn btn-sm">← Garuka kuri Umubyeyi</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="legal-page">
      <Link href="/" className="legal-back">← Home</Link>
      <h1>End User License Agreement</h1>
      <div className="legal-updated">Last updated: July 26, 2026</div>

      <div className="legal-summary">
        <b>In short:</b> Umubyeyi is a research project, not a medical service. It does not
        replace a doctor or emergency care. If you are in danger, call 114 or go to your nearest
        health facility right away.
      </div>

      <p>
        Umubyeyi is a free, non-commercial academic capstone project (BSc Software Engineering,
        African Leadership University) providing bilingual (Kinyarwanda/English) emotional
        wellbeing information, a guided screening check-in, and an EPDS-10 wellness self-assessment
        for first-time mothers. By using Umubyeyi, you agree to the terms below.
      </p>

      <h2>1. Not medical care</h2>
      <p>
        Umubyeyi provides general educational and emotional-support information only. It is not
        emergency care, medical advice, diagnosis, or treatment, and using it does not create a
        doctor-patient or clinical relationship of any kind. The guided check-in and EPDS-10 test
        estimate screening risk based on patterns in a research dataset; they do not diagnose
        postpartum depression or any other condition. If you are in crisis or in danger, contact
        Rwanda&apos;s emergency line (114) or your nearest health facility immediately rather than
        relying on this app.
      </p>

      <h2>2. Research-prototype limitations</h2>
      <p>You understand and accept that Umubyeyi is a research prototype, not a validated clinical product:</p>
      <ul>
        <li>Its screening-risk model was trained on a licensed dataset of postpartum participants
          in Bangladesh, not Rwanda, and its accuracy for the intended Rwandan population has not
          been separately validated.</li>
        <li>The Kinyarwanda wording used throughout the app, including the EPDS-10 wellness test,
          is authored by this project and has not been reviewed by a clinician or a native-speaker
          translator.</li>
        <li>Responses generated by the chat feature (whether from the external AI provider or this
          project&apos;s own fine-tuned model) are produced automatically and may occasionally be
          incomplete, imprecise, or miss context; they are not reviewed by a person before being
          shown to you.</li>
      </ul>

      <h2>3. Eligibility</h2>
      <p>
        Umubyeyi is intended for adult users and is not directed at children. The guided check-in
        requires a stated age between 18 and 60.
      </p>

      <h2>4. Acceptable use</h2>
      <p>
        You agree to use Umubyeyi only for its intended purpose (personal, non-commercial,
        informational and emotional-wellbeing support) and not to attempt to disrupt,
        reverse-engineer for harmful purposes, or misuse the service in a way that could affect its
        availability to other users.
      </p>

      <h2>5. Third-party services</h2>
      <p>
        Umubyeyi&apos;s chat feature sends your messages to a third-party AI service (Groq) to
        generate responses, as described in the{" "}
        <Link href="/privacy">Privacy Policy</Link>. Your use of Umubyeyi&apos;s chat feature is
        also subject to that provider&apos;s own terms.
      </p>

      <h2>6. No warranty</h2>
      <p>
        Umubyeyi is provided &quot;as is&quot; and &quot;as available,&quot; without warranties of
        any kind, express or implied, including as to accuracy, reliability, or fitness for a
        particular purpose. As an academic project, it is not offered with any commercial
        service-level guarantee of uptime, support, or correctness.
      </p>

      <h2>7. Limitation of liability</h2>
      <p>
        To the fullest extent permitted by applicable law, the author is not liable for any
        damages, harm, or loss arising from your use of, or inability to use, Umubyeyi, including
        reliance on any screening result, chat response, or self-assessment outcome. Umubyeyi is
        not a substitute for professional medical or mental-health care.
      </p>

      <h2>8. Intellectual property</h2>
      <p>
        Umubyeyi&apos;s source code, content, and design are the work of its author, created for an
        academic capstone project, and are provided under the terms of the project&apos;s public
        repository. Certain underlying datasets and models used to train Umubyeyi&apos;s screening
        and generation features carry their own separate licenses (for example, the
        Mendeley-hosted postpartum-depression dataset, licensed CC BY 4.0); see the project&apos;s
        repository documentation for full attribution.
      </p>

      <h2>9. Local data and termination</h2>
      <p>
        You may stop using Umubyeyi at any time. Because all of your data is stored locally in
        your own browser, you can remove it yourself at any time by clearing your browser&apos;s
        site data or using the in-app &quot;Forgot PIN → Reset everything&quot; option; there is no
        account to close and no server-side copy to delete.
      </p>

      <h2>10. Changes to these terms</h2>
      <p>
        These terms may be updated as the project develops. Continued use of Umubyeyi after an
        update means you accept the revised terms.
      </p>

      <h2>11. Governing context</h2>
      <p>
        Umubyeyi is an academic capstone project, not a commercial legal entity. These terms are
        provided in good faith to set clear expectations for users, rather than as a substitute for
        formal legal advice.
      </p>

      <div className="legal-footer-links">
        <Link href="/privacy" className="btn btn-sm">Privacy Policy</Link>
        <Link href="/" className="btn btn-sm">← Back to Umubyeyi</Link>
      </div>
    </div>
  );
}
