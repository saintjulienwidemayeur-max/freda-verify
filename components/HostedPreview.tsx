"use client";
import { useMemo, useState } from "react";

export type Lang = "fr" | "en" | "ht";
export type Theme = "light" | "dark";
export type Shape = "square" | "rounded" | "pill";
export type DocKey = "id" | "passport" | "license";
export type Step = "welcome" | "country" | "document" | "selfie" | "done";
export const STEPS: Step[] = ["welcome", "country", "document", "selfie", "done"];

export type Cfg = {
  name: string; logo: string | null; color: string; theme: Theme; shape: Shape; lang: Lang;
  title: string; subtitle: string; docs: Record<DocKey, boolean>; domain: string; redirect: string;
  support: string; hidePowered: boolean;
};

type Dict = {
  titleFor: string; sub: string; step: string; idv: string; facev: string; start: string;
  agreePre: string; agreePost: string; secured: string; help: string;
  countryT: string; countryS: string; search: string; none: string; cont: string;
  docT: string; docS: string; issued: string; change: string; id: string; passport: string; license: string;
  photoArea: string;
  idS: string; passportS: string; licenseS: string; tips: string;
  selfieT: string; selfieS: string; selfieB: string; selfieTips: string;
  doneT: string; doneS: string; resOk: string; resOkS: string; resNo: string; resNoS: string; back: string; redirect: string;
  frontT: string; frontS: string; backT: string; backS: string; pageT: string; pageS: string;
  takeCam: string; upload: string; retake: string; useAnyway: string; capture: string; cancel: string; camDenied: string;
  qGood: string; qDark: string; qBright: string; qBlur: string; reviewT: string; reviewS: string; submit: string;
  scanPlace: string; scanFace: string; scanHold: string; scanDark: string; scanGlare: string; scanBlur: string; scanAuto: string; scanDone: string; capNow: string;
  scanLoading: string; scanCloser: string; scanFar: string; scanCenter: string; scanFound: string;
  qrTitle: string; qrSub: string; qrWhy: string; qrCopy: string; qrCopied: string; qrHere: string;
  faceLoading: string; faceNone: string; faceMulti: string; faceSmall: string; faceBig: string; faceCenter: string; faceFront: string;
  turnL: string; turnR: string; turnWrong: string; turnOk: string; turnAgain: string; dirL: string; dirR: string; stepFace: string; stepTurn: string;
  scanFail: string; retry: string; showPassport: string; showId: string; docRej: string; rejShape: string; rejFace: string; rejMrz: string; rejLight: string; rejUnavail: string; checkPhoto: string;
  blinkNow: string; stepAction: string; tipMore: string;
  scanFit: string; scanGuide: string; waitMsgs: string[]; waitFace: string[]; sendNote: string; sendFail: string; demoBanner: string; demoDone: string; demoDoneT: string; lblFront: string; lblBack: string; lblSelfie: string; lblPage: string;
};

export const T: Record<Lang, Dict> = {
  en: {
    titleFor: "Verification for", sub: "Follow these quick steps to confirm your identity", step: "Step", idv: "ID verification", facev: "Face verification",
    start: "Start verification", agreePre: "By starting you agree to", agreePost: "and to the processing of your identity data.",
    secured: "Secured by", help: "Need help?",
    countryT: "Where was your document issued?", countryS: "Select the country that issued your ID document.", search: "Search country", none: "No country found", cont: "Continue",
    docT: "Choose your document", docS: "Select the document you want to use.", issued: "Issued in", change: "Change",
    id: "National ID card", passport: "Passport", license: "Driver's license",
    photoArea: "Your photo must be clearly visible in this area (no finger, no glare).", idS: "Front and back", passportS: "Photo page", licenseS: "Front and back", tips: "Good lighting · No glare · All corners visible",
    selfieT: "Take a selfie", selfieS: "Center your face in the oval. We will then ask you to turn your head left or right.", selfieB: "Take selfie", selfieTips: "Remove glasses · Neutral face · Good light",
    doneT: "Verification submitted", doneS: "Thank you! We are reviewing your information. You will be notified of the result shortly.", resOk: "Identity verified", resOkS: "Your verification was approved. You can go back to the service.", resNo: "Verification not approved", resNoS: "We could not approve your verification. Please contact the service for help.", back: "Back to", redirect: "You will be redirected automatically.",
    frontT: "Front of your document", frontS: "Show the FRONT: the side with your photo and your name.", backT: "Back of your document", backS: "Now turn it over and show the BACK: the side with the lines of characters at the bottom.", pageT: "Passport photo page", pageS: "Open the passport to the photo page.",
    takeCam: "Use camera", upload: "Choose a photo already on my phone", retake: "Retake", useAnyway: "Use anyway", capture: "Capture", cancel: "Cancel", camDenied: "Camera unavailable. You can upload a photo instead.",
    qGood: "Looks good", qDark: "Too dark — find better light", qBright: "Too bright or glare", qBlur: "Blurry — hold steady", reviewT: "Review your photos", reviewS: "Make sure everything is clear and readable.", submit: "Submit",
    scanPlace: "Place the document inside the frame", scanFace: "Center your face in the oval", scanHold: "Hold steady…", scanDark: "Not enough light: move to a brighter place", scanGlare: "Reflection on the card: tilt it slightly", scanBlur: "Image is blurry: move the phone back (about 25 cm), hold still and wait for it to focus", scanAuto: "Automatic capture", scanDone: "Captured!", capNow: "Take photo",
    scanLoading: "Preparing the scanner…", scanCloser: "Bring the card closer: it must fill the frame", scanFar: "Move back a little: the whole card must be inside the frame", scanCenter: "Center the card in the frame", scanFound: "Document detected",
    qrTitle: "Continue on your phone", qrSub: "Scan this QR code with your phone camera to continue the verification.", qrWhy: "Your phone camera takes much better photos of your document and face.", qrCopy: "Copy link", qrCopied: "Link copied", qrHere: "Continue on this computer",
    faceLoading: "Preparing face detection…", faceNone: "No face detected — center your face in the oval", faceMulti: "Only one person in the frame, please", faceSmall: "Move a little closer", faceBig: "Move back a little", faceCenter: "Center your face in the oval", faceFront: "Look straight at the camera",
    turnL: "Slowly turn your head to the LEFT", turnR: "Slowly turn your head to the RIGHT", turnWrong: "Other way — turn to your", turnOk: "Perfect!", turnAgain: "Let's try again", dirL: "LEFT", dirR: "RIGHT", stepFace: "Face", stepTurn: "Turn",
    scanFail: "The scanner could not be loaded. Check your connection and try again.", retry: "Try again", showPassport: "Show the passport photo page (the page with your photo)", showId: "Show your ID card inside the frame",
    docRej: "Document not recognised", rejShape: "This does not look like the right document. Show it flat, fully inside the frame.", rejFace: "We cannot see the photo on the document. Make sure it is visible and well lit.", rejMrz: "The two lines of characters at the bottom of the passport page are not fully visible. Keep the whole page flat in the frame, with a little space on the left and right of those two lines.", checkPhoto: "Check the photo: you must be able to read ALL the text, with no glare and nothing cut off. If it is not clear, tap Retake.", rejLight: "We cannot read this photo clearly. Go to a bright place (daylight is best), hold the document flat and steady, and take it again.", rejUnavail: "We cannot check this document right now. Please try again.",
    blinkNow: "Now blink your eyes slowly", stepAction: "Action", tipMore: "Turn a little more",
    scanFit: "Fit the photo page inside the frame: your photo on the left, the two lines of characters at the bottom. Lay it flat, good light.", waitFace: ["Scanning your face…", "Please wait a moment…", "Don't leave, almost done…", "Checking your photo…"], waitMsgs: ["Scanning your document…", "Please wait a moment…", "Don't leave, almost done…", "Reading the text on your document…", "Just a few more seconds…"], scanGuide: "Checking the page… hold still.", sendNote: "Your photos and a short video of the head-turn step are sent securely to {n} and reviewed by a person. They are stored encrypted.", sendFail: "We could not send your photo. Check your connection and try again.", demoBanner: "Demo mode · nothing is uploaded", demoDone: "This is a demo. Your photos stayed on your device and were deleted from this page. No verification was performed.", demoDoneT: "Demo complete", lblFront: "Front", lblBack: "Back", lblSelfie: "Selfie", lblPage: "Photo page",
  },
  fr: {
    titleFor: "Vérification pour", sub: "Suivez ces étapes rapides pour confirmer votre identité", step: "Étape", idv: "Vérification de la pièce", facev: "Vérification du visage",
    start: "Commencer la vérification", agreePre: "En commençant, vous acceptez les", agreePost: "et le traitement de vos données d'identité.",
    secured: "Sécurisé par", help: "Besoin d'aide ?",
    countryT: "Où votre document a-t-il été émis ?", countryS: "Choisissez le pays qui a émis votre pièce d'identité.", search: "Rechercher un pays", none: "Aucun pays trouvé", cont: "Continuer",
    docT: "Choisissez votre document", docS: "Sélectionnez le document que vous souhaitez utiliser.", issued: "Émis en", change: "Modifier",
    id: "Carte d'identité nationale", passport: "Passeport", license: "Permis de conduire",
    photoArea: "Votre photo doit être bien visible dans cette zone (sans doigt ni reflet).", idS: "Recto et verso", passportS: "Page photo", licenseS: "Recto et verso", tips: "Bon éclairage · Sans reflet · Coins visibles",
    selfieT: "Prenez un selfie", selfieS: "Centrez votre visage dans l'ovale. Nous vous demanderons ensuite de tourner la tête à gauche ou à droite.", selfieB: "Prendre le selfie", selfieTips: "Sans lunettes · Visage neutre · Bonne lumière",
    doneT: "Vérification envoyée", doneS: "Merci ! Nous examinons vos informations. Vous serez informé du résultat sous peu.", resOk: "Identité vérifiée", resOkS: "Votre vérification a été approuvée. Vous pouvez retourner au service.", resNo: "Vérification non approuvée", resNoS: "Nous n'avons pas pu approuver votre vérification. Contactez le service pour de l'aide.", back: "Retour à", redirect: "Vous serez redirigé automatiquement.",
    frontT: "Recto de votre document", frontS: "Montrez le RECTO : le côté avec votre photo et votre nom.", backT: "Verso de votre document", backS: "Retournez-le et montrez le VERSO : le côté avec les lignes de caractères en bas.", pageT: "Page photo du passeport", pageS: "Ouvrez le passeport à la page photo.",
    takeCam: "Utiliser la caméra", upload: "Choisir une photo déjà dans mon téléphone", retake: "Reprendre", useAnyway: "Utiliser quand même", capture: "Capturer", cancel: "Annuler", camDenied: "Caméra indisponible. Vous pouvez téléverser une photo.",
    qGood: "Image correcte", qDark: "Trop sombre — cherchez plus de lumière", qBright: "Trop clair ou reflet", qBlur: "Flou — restez stable", reviewT: "Vérifiez vos photos", reviewS: "Assurez-vous que tout est net et lisible.", submit: "Envoyer",
    scanPlace: "Placez le document dans le cadre", scanFace: "Centrez votre visage dans l'ovale", scanHold: "Ne bougez pas…", scanDark: "Pas assez de lumière : allez dans un endroit plus éclairé", scanGlare: "Reflet sur la carte : inclinez-la légèrement", scanBlur: "Image floue : éloignez le téléphone (environ 25 cm), restez stable et attendez la mise au point", scanAuto: "Capture automatique", scanDone: "Capturé !", capNow: "Prendre la photo",
    scanLoading: "Préparation du scanner…", scanCloser: "Approchez la carte : elle doit remplir le cadre", scanFar: "Reculez un peu : toute la carte doit être dans le cadre", scanCenter: "Centrez la carte dans le cadre", scanFound: "Document détecté",
    qrTitle: "Continuez sur votre téléphone", qrSub: "Scannez ce code QR avec l'appareil photo de votre téléphone pour poursuivre la vérification.", qrWhy: "La caméra de votre téléphone prend de bien meilleures photos de votre document et de votre visage.", qrCopy: "Copier le lien", qrCopied: "Lien copié", qrHere: "Continuer sur cet ordinateur",
    faceLoading: "Préparation de la détection du visage…", faceNone: "Aucun visage détecté — centrez votre visage dans l'ovale", faceMulti: "Une seule personne dans le cadre, s'il vous plaît", faceSmall: "Rapprochez-vous un peu", faceBig: "Reculez un peu", faceCenter: "Centrez votre visage dans l'ovale", faceFront: "Regardez droit devant vous",
    turnL: "Tournez lentement la tête vers la GAUCHE", turnR: "Tournez lentement la tête vers la DROITE", turnWrong: "Dans l'autre sens — tournez vers votre", turnOk: "Parfait !", turnAgain: "Réessayons", dirL: "GAUCHE", dirR: "DROITE", stepFace: "Visage", stepTurn: "Tourner",
    scanFail: "Le scanner n'a pas pu être chargé. Vérifiez votre connexion et réessayez.", retry: "Réessayer", showPassport: "Montrez la page photo du passeport (la page avec votre photo)", showId: "Montrez votre carte d'identité dans le cadre",
    docRej: "Document non reconnu", rejShape: "Ce n'est pas le bon document. Présentez-le à plat, entièrement dans le cadre.", rejFace: "Nous ne voyons pas la photo du document. Assurez-vous qu'elle est visible et bien éclairée.", rejMrz: "Les deux lignes de caractères en bas de la page du passeport ne sont pas entièrement visibles. Gardez toute la page à plat dans le cadre, avec un peu d'espace à gauche et à droite de ces deux lignes.", checkPhoto: "Vérifiez la photo : vous devez pouvoir lire TOUT le texte, sans reflet et sans rien de coupé. Si ce n'est pas net, touchez Reprendre.", rejLight: "Nous ne pouvons pas lire cette photo clairement. Allez dans un endroit bien éclairé (la lumière du jour est idéale), tenez le document à plat sans bouger, puis reprenez la photo.", rejUnavail: "Nous ne pouvons pas vérifier ce document pour le moment. Veuillez réessayer.",
    blinkNow: "Maintenant, clignez lentement des yeux", stepAction: "Action", tipMore: "Tournez un peu plus",
    scanFit: "Placez la page photo dans le cadre : votre photo à gauche, les deux lignes de caractères en bas. À plat, bonne lumière.", waitFace: ["Analyse de votre visage…", "Merci de patienter un instant…", "Ne quittez pas, ça arrive…", "Vérification de votre photo…"], waitMsgs: ["Analyse de votre document…", "Merci de patienter un instant…", "Ne quittez pas, ça arrive…", "Lecture du texte de votre document…", "Encore quelques secondes…"], scanGuide: "Vérification de la page… ne bougez pas.", sendNote: "Vos photos et une courte vidéo de l'étape où vous tournez la tête sont envoyées de façon sécurisée à {n} et examinées par une personne. Elles sont conservées chiffrées.", sendFail: "Impossible d'envoyer votre photo. Vérifiez votre connexion et réessayez.", demoBanner: "Mode démo · rien n'est envoyé", demoDone: "Ceci est une démo. Vos photos sont restées sur votre appareil et ont été supprimées de cette page. Aucune vérification n'a été effectuée.", demoDoneT: "Démo terminée", lblFront: "Recto", lblBack: "Verso", lblSelfie: "Selfie", lblPage: "Page photo",
  },
  ht: {
    titleFor: "Verifikasyon pou", sub: "Swiv etap rapid sa yo pou konfime idantite w", step: "Etap", idv: "Verifikasyon pyès", facev: "Verifikasyon vizaj",
    start: "Kòmanse verifikasyon", agreePre: "Lè w kòmanse, ou aksepte", agreePost: "ak trètman done idantite w.",
    secured: "Sekirize pa", help: "Bezwen èd?",
    countryT: "Ki peyi ki bay dokiman w lan?", countryS: "Chwazi peyi ki bay pyès idantite w la.", search: "Chèche yon peyi", none: "Pa jwenn peyi a", cont: "Kontinye",
    docT: "Chwazi dokiman w", docS: "Chwazi dokiman ou vle itilize a.", issued: "Bay nan", change: "Chanje",
    id: "Kat idantite nasyonal", passport: "Paspò", license: "Pèmi kondwi",
    photoArea: "Foto w dwe parèt byen klè nan zòn sa a (pa gen dwèt, pa gen refle).", idS: "Devan ak dèyè", passportS: "Paj foto a", licenseS: "Devan ak dèyè", tips: "Bon limyè · Pa gen refle · Tout kwen yo vizib",
    selfieT: "Pran yon selfi", selfieS: "Mete figi w nan ovòl la. Apre nou pral mande w vire tèt ou goch oswa dwat.", selfieB: "Pran selfi a", selfieTips: "Retire linèt · Figi nòmal · Bon limyè",
    doneT: "Verifikasyon an voye", doneS: "Mèsi! N ap egzamine enfòmasyon w yo. N ap enfòme w rezilta a talè.", resOk: "Idantite verifye", resOkS: "Verifikasyon w apwouve. Ou ka retounen nan sèvis la.", resNo: "Verifikasyon an pa apwouve", resNoS: "Nou pa t kapab apwouve verifikasyon w. Kontakte sèvis la pou jwenn èd.", back: "Retounen sou", redirect: "W ap retounen otomatikman.",
    frontT: "Devan dokiman w", frontS: "Montre DEVAN an: bò ki gen foto w ak non w.", backT: "Dèyè dokiman w", backS: "Kounye a vire l epi montre DÈYÈ a: bò ki gen liy karaktè yo anba.", pageT: "Paj foto paspò a", pageS: "Louvri paspò a nan paj foto a.",
    takeCam: "Itilize kamera", upload: "Chwazi yon foto ki deja nan telefòn mwen", retake: "Refè", useAnyway: "Itilize l kanmenm", capture: "Pran foto", cancel: "Anile", camDenied: "Kamera pa disponib. Ou ka voye yon foto.",
    qGood: "Foto a bon", qDark: "Twò nwa — chèche plis limyè", qBright: "Twò klè oswa gen refle", qBlur: "Flou — pa bouje", reviewT: "Revize foto w yo", reviewS: "Asire w tout bagay klè epi lizib.", submit: "Voye",
    scanPlace: "Mete dokiman an andedan kadre a", scanFace: "Mete figi w nan ovòl la", scanHold: "Pa bouje…", scanDark: "Pa gen ase limyè: ale yon kote ki pi klere", scanGlare: "Gen yon refle sou kat la: enkline l yon ti jan", scanBlur: "Imaj la flou: lwen telefòn nan (anviwon 25 cm), pa bouje epi tann li fè mizajou fokis la", scanAuto: "Kapti otomatik", scanDone: "Kaptire!", capNow: "Pran foto a",
    scanLoading: "N ap prepare eskanè a…", scanCloser: "Avanse kat la: li dwe ranpli kadre a", scanFar: "Fè yon ti bak: tout kat la dwe andedan kadre a", scanCenter: "Mete kat la nan mitan kadre a", scanFound: "Dokiman an detekte",
    qrTitle: "Kontinye sou telefòn ou", qrSub: "Eskane kòd QR sa a ak kamera telefòn ou pou kontinye verifikasyon an.", qrWhy: "Kamera telefòn ou pran pi bon foto dokiman w ak figi w.", qrCopy: "Kopye lyen an", qrCopied: "Lyen an kopye", qrHere: "Kontinye sou òdinatè sa a",
    faceLoading: "N ap prepare deteksyon figi a…", faceNone: "Pa gen figi detekte — mete figi w nan ovòl la", faceMulti: "Yon sèl moun nan kadre a, tanpri", faceSmall: "Pwoche yon ti jan", faceBig: "Rekile yon ti jan", faceCenter: "Mete figi w nan mitan ovòl la", faceFront: "Gade dirèk kamera a",
    turnL: "Vire tèt ou dousman sou bò GOCH", turnR: "Vire tèt ou dousman sou bò DWAT", turnWrong: "Lòt bò — vire sou bò", turnOk: "Pafè!", turnAgain: "Ann eseye ankò", dirL: "GOCH", dirR: "DWAT", stepFace: "Figi", stepTurn: "Vire",
    scanFail: "Pa t kapab chaje eskanè a. Verifye koneksyon w epi eseye ankò.", retry: "Eseye ankò", showPassport: "Montre paj foto paspò a (paj ki gen foto w la)", showId: "Montre kat idantite w andedan kadre a",
    docRej: "Pa rekonèt dokiman an", rejShape: "Sa pa sanble ak bon dokiman an. Montre l plat, tout antye andedan kadre a.", rejFace: "Nou pa wè foto a sou dokiman an. Asire w li vizib epi byen klere.", rejMrz: "De liy karaktè ki anba paj paspò a pa vizib nèt. Kenbe tout paj la plat nan kadre a, ak yon ti espas sou kote goch ak dwat de liy sa yo.", checkPhoto: "Gade foto a: ou dwe ka li TOUT tèks la, san reflè epi san anyen ki koupe. Si li pa klè, peze Refè.", rejLight: "Nou pa ka li foto sa a byen klè. Ale yon kote ki klere (limyè jou a pi bon), kenbe dokiman an plat epi san bouje, epi pran foto a ankò.", rejUnavail: "Nou pa ka verifye dokiman sa a kounye a. Tanpri eseye ankò.",
    blinkNow: "Kounye a bat je w dousman", stepAction: "Aksyon", tipMore: "Vire yon ti jan plis",
    scanFit: "Mete paj foto a nan kad la: foto w a agoch, de liy karaktè yo anba. Mete l plat, ak bon limyè.", waitFace: ["N ap eskane vizaj ou…", "Tanpri, tann yon ti moman…", "Pa kite paj la, li prèske fini…", "N ap tcheke foto w la…"], waitMsgs: ["N ap eskane dokiman w lan…", "Tanpri, tann yon ti moman…", "Pa kite paj la, li prèske fini…", "N ap li tèks ki sou dokiman w lan…", "Kèk segonn ankò…"], scanGuide: "N ap tcheke paj la… pa bouje.", sendNote: "Foto w yo ak yon ti videyo etap kote w vire tèt la voye an sekirite bay {n} epi yon moun egzamine yo. Yo konsève chifre.", sendFail: "Nou pa t ka voye foto w la. Verifye koneksyon w epi eseye ankò.", demoBanner: "Mòd demo · anyen pa voye", demoDone: "Sa a se yon demo. Foto w yo rete sou aparèy ou epi yo efase nan paj la. Pa gen verifikasyon ki fèt.", demoDoneT: "Demo fini", lblFront: "Devan", lblBack: "Dèyè", lblSelfie: "Selfi", lblPage: "Paj foto",
  },
};

export const COUNTRIES = ["HT", "DO", "US", "CA", "FR", "BE", "CH", "GB", "ES", "DE", "BS", "JM", "TC", "PA", "MX", "CO", "BR", "CL", "AR", "SN", "CI", "CM", "NG", "GH"];
export const flag = (cc: string) => String.fromCodePoint(...[...cc].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65));
export const RADIUS: Record<Shape, number> = { square: 6, rounded: 14, pill: 999 };
export const LANGS: Lang[] = ["en", "fr", "ht"];

export const onColor = (hex: string) => {
  const n = parseInt(hex.slice(1), 16), r = n >> 16, g = (n >> 8) & 255, b = n & 255;
  return 0.299 * r + 0.587 * g + 0.114 * b > 160 ? "#0A1647" : "#FFFFFF";
};
export const termsLabel = (l: Lang, n: string) => (l === "en" ? `${n}'s Terms and Conditions` : l === "fr" ? `Conditions d'utilisation de ${n}` : `Kondisyon itilizasyon ${n}`);
export const fold = (v: string) => v.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
export const isMail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

export const Ic = ({ d, className = "h-4 w-4" }: { d: string; className?: string }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d={d} /></svg>
);
export const DOC_ICON: Record<DocKey, string> = {
  id: "M3 6.5A1.5 1.5 0 0 1 4.5 5h15A1.5 1.5 0 0 1 21 6.5v11a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5zM8.5 12.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM5.5 16c.5-1.600 1.600-2.400 3-2.400s2.500.8 3 2.400M14 9.5h4M14 13h4",
  passport: "M6 3h11a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM11.5 14a3.500 3.500 0 1 0 0-7 3.500 3.500 0 0 0 0 7zM8 10.5h7M11.5 7c1 1 1.400 2.200 1.400 3.500S12.500 13 11.500 14M8.500 17.500h6",
  license: "M3 6.5A1.5 1.5 0 0 1 4.5 5h15A1.5 1.5 0 0 1 21 6.5v11a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5zM6 9h6M6 12h4M14.500 15.500l1.500-4h1l1.500 4M15 14h2.500",
};

export default function HostedPreview({ c, step, go, setLang }: { c: Cfg; step: Step; go: (s: Step) => void; setLang: (l: Lang) => void }) {
  const t = T[c.lang];
  const [country, setCountry] = useState("HT");
  const [q, setQ] = useState("");
  const [langOpen, setLangOpen] = useState(false);

  const dark = c.theme === "dark", fg = onColor(c.color), r = RADIUS[c.shape];
  const bg = dark ? "#0A1647" : "#FFFFFF", tx = dark ? "#FFFFFF" : "#0A1647";
  const mut = dark ? "rgba(255,255,255,.62)" : "rgba(10,22,71,.55)", line = dark ? "rgba(255,255,255,.14)" : "#E6ECF7";
  const soft = dark ? "rgba(255,255,255,.06)" : "#F5F7FC";
  const tint = `${c.color}1A`;
  const custom = c.name.trim().length > 0;
  const name = c.name.trim() || "Freda Verify"; // default brand when the client has not filled the white label
  const card = Math.min(r, 16);

  const names = useMemo(() => {
    let dn: Intl.DisplayNames | null = null;
    try { dn = new Intl.DisplayNames([c.lang === "ht" ? "fr" : c.lang], { type: "region" }); } catch { dn = null; }
    return Object.fromEntries(COUNTRIES.map((cc) => [cc, dn?.of(cc) ?? cc])) as Record<string, string>;
  }, [c.lang]);
  const list = COUNTRIES.filter((cc) => fold(names[cc]).includes(fold(q)));
  const docs = (["id", "passport", "license"] as DocKey[]).filter((k) => c.docs[k]);
  const progress = { welcome: 0, country: 0.25, document: 0.5, selfie: 0.75, done: 1 }[step];
  const prev: Partial<Record<Step, Step>> = { country: "welcome", document: "country", selfie: "document" };

  const Btn = ({ children, onClick, disabled }: { children: React.ReactNode; onClick?: () => void; disabled?: boolean }) => (
    <button type="button" onClick={onClick} disabled={disabled}
      className="w-full py-3 text-[13px] font-semibold transition-opacity hover:opacity-90 disabled:opacity-40" style={{ background: c.color, color: fg, borderRadius: r }}>{children}</button>
  );
  const Logo = ({ size = 34 }: { size?: number }) => c.logo
    // eslint-disable-next-line @next/next/no-img-element
    ? <img src={c.logo} alt="" style={{ height: size, maxWidth: 150 }} className="object-contain" />
    : !custom
      // eslint-disable-next-line @next/next/no-img-element
      ? <img src="/logo-mark.svg" alt="Freda Verify" style={{ height: size, width: size }} />
      : <span className="grid place-items-center rounded-xl font-bold" style={{ width: size, height: size, background: c.color, color: fg, fontSize: size * 0.42 }}>{name[0]?.toUpperCase()}</span>;
  const Secured = () => c.hidePowered ? null : (
    <div className="mt-2 flex items-center justify-center gap-1.5 text-[9px]" style={{ color: mut }}>
      {t.secured}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo-mark.svg" alt="" className="h-3.5 w-3.5" style={dark ? { filter: "brightness(1.6)" } : undefined} />
      <span className="font-semibold">Freda Verify</span>
    </div>
  );
  const TopBar = () => (
    <div className="flex items-center gap-3 px-5 pt-1">
      <button type="button" onClick={() => prev[step] && go(prev[step]!)} aria-label="Back"
        className="grid h-8 w-8 shrink-0 place-items-center rounded-full" style={{ background: soft }}><Ic d="M15 6l-6 6 6 6" /></button>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ background: line }}>
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${progress * 100}%`, background: c.color }} />
      </div>
      <span className="text-[10px] tabular-nums" style={{ color: mut }}>{Math.round(progress * 4)}/4</span>
    </div>
  );

  return (
    <div className="relative mx-auto w-[290px] rounded-[2.6rem] bg-[#111] p-[9px] shadow-[0_24px_60px_rgba(10,22,71,.28)]" aria-label={`Preview of the hosted verification page: ${step}`}>
      <div className="relative flex h-[600px] flex-col overflow-hidden rounded-[2.1rem]" style={{ background: bg, color: tx }}>
        {/* status bar */}
        <div className="relative flex h-10 shrink-0 items-center justify-between px-6 text-[11px] font-semibold">
          <span>9:41</span>
          <span className="absolute left-1/2 top-2 h-[22px] w-[84px] -translate-x-1/2 rounded-full bg-[#111]" />
          <span className="flex items-center gap-1"><Ic d="M2 18h2M7 15h2v3M12 11h2v7M17 7h2v11" className="h-3 w-3" /><span className="h-2.5 w-5 rounded-[3px] border" style={{ borderColor: tx }}><span className="block h-full w-3/4 rounded-[1px]" style={{ background: tx }} /></span></span>
        </div>

        {step !== "welcome" && step !== "done" && <TopBar />}

        <div className="flex min-h-0 flex-1 flex-col px-5 pb-3">
          {step === "welcome" && (<>
            <div className="relative mt-1 flex justify-end">
              <button type="button" onClick={() => setLangOpen(!langOpen)} aria-label="Language" aria-expanded={langOpen}
                className="flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-[11px] font-medium" style={{ background: soft }}>
                <Ic d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3.600 9h16.800M3.600 15h16.800M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" className="h-3.5 w-3.5" />
                {c.lang.toUpperCase()}<Ic d="M6 9l6 6 6-6" className="h-3 w-3" />
              </button>
              {langOpen && (
                <ul className="absolute right-0 top-9 z-10 w-28 overflow-hidden rounded-xl text-[11px] shadow-lg" style={{ background: bg, border: `1px solid ${line}` }}>
                  {LANGS.map((l) => (
                    <li key={l}><button type="button" onClick={() => { setLang(l); setLangOpen(false); }} className="flex w-full items-center justify-between px-3 py-2 text-left" style={{ background: l === c.lang ? tint : "transparent" }}>
                      {{ en: "English", fr: "Français", ht: "Kreyòl" }[l]}{l === c.lang && <span style={{ color: c.color }}>✓</span>}</button></li>
                  ))}
                </ul>
              )}
            </div>
            <div className="mt-3 flex flex-col items-center text-center">
              <Logo />
              <h3 className="mt-3 font-display text-[22px] font-extrabold leading-[1.1] tracking-tight">{c.title.trim() || `${t.titleFor} ${name}`}</h3>
              <p className="mt-2 text-[12px] leading-snug" style={{ color: mut }}>{c.subtitle.trim() || t.sub}</p>
            </div>
            <div className="flex flex-1 items-center justify-center">
              <ol className="relative space-y-5 pl-5">
                <span className="absolute left-0 top-0 h-full w-[3px] rounded-full" style={{ background: line }} />
                <span className="absolute left-0 top-0 h-1/2 w-[3px] rounded-full" style={{ background: `linear-gradient(${c.color}, ${c.color}66)` }} />
                {[t.idv, t.facev].map((x, i) => (
                  <li key={x}>
                    <div className="text-[9px] font-semibold uppercase tracking-[0.18em]" style={{ color: mut }}>{t.step} {i + 1}</div>
                    <div className="text-[15px] font-bold" style={{ color: i === 0 ? tx : mut }}>{x}</div>
                  </li>
                ))}
              </ol>
            </div>
            <Btn onClick={() => go("country")}>{t.start}</Btn>
            <p className="mt-2.5 text-center text-[9.5px] leading-snug" style={{ color: mut }}>
              {t.agreePre} <span className="font-medium" style={{ color: c.color }}>{termsLabel(c.lang, name)}</span> {t.agreePost}
            </p>
            {isMail(c.support) && <p className="mt-1 break-all text-center text-[9px]" style={{ color: mut }}>{t.help} {c.support}</p>}
            <Secured />
          </>)}

          {step === "country" && (<>
            <h3 className="mt-4 font-display text-[19px] font-extrabold leading-tight tracking-tight">{t.countryT}</h3>
            <p className="mt-1 text-[12px]" style={{ color: mut }}>{t.countryS}</p>
            <label className="mt-3 flex items-center gap-2 px-3 py-2.5 text-[12px] focus-within:ring-2" style={{ background: soft, borderRadius: card, ["--tw-ring-color" as string]: c.color }}>
              <Ic d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4" className="h-3.5 w-3.5 shrink-0" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.search} aria-label={t.search}
                className="w-full bg-transparent outline-none placeholder:opacity-60 focus-visible:outline-none" style={{ color: tx }} />
            </label>
            <ul className="-mx-1 mt-2 min-h-0 flex-1 overflow-y-auto px-1 [scrollbar-width:thin]" role="listbox" aria-label={t.countryT}>
              {list.length === 0 && <li className="py-6 text-center text-[12px]" style={{ color: mut }}>{t.none}</li>}
              {list.map((cc) => {
                const on = cc === country;
                return (
                  <li key={cc} role="option" aria-selected={on}>
                    <button type="button" onClick={() => setCountry(cc)} className="flex w-full items-center gap-3 px-2.5 py-2 text-left text-[13px]"
                      style={{ background: on ? tint : "transparent", borderRadius: card }}>
                      <span className="text-[18px] leading-none">{flag(cc)}</span>
                      <span className={on ? "font-semibold" : ""}>{names[cc]}</span>
                      {on && <span className="ml-auto grid h-4 w-4 place-items-center rounded-full" style={{ background: c.color, color: fg }}><Ic d="M5 12.5l4.500 4.500L19 7.500" className="h-2.5 w-2.5" /></span>}
                    </button>
                  </li>
                );
              })}
            </ul>
            <div className="pt-3"><Btn onClick={() => go("document")}>{t.cont}</Btn></div>
            <Secured />
          </>)}

          {step === "document" && (<>
            <h3 className="mt-4 font-display text-[19px] font-extrabold leading-tight tracking-tight">{t.docT}</h3>
            <p className="mt-1 text-[12px]" style={{ color: mut }}>{t.docS}</p>
            <div className="mt-3 flex items-center gap-2 px-3 py-2 text-[11.5px]" style={{ background: soft, borderRadius: card }}>
              <span className="text-[16px] leading-none">{flag(country)}</span>
              <span className="shrink-0" style={{ color: mut }}>{t.issued}</span><span className="min-w-0 truncate font-semibold">{names[country]}</span>
              <button type="button" onClick={() => go("country")} className="ml-auto shrink-0 font-semibold" style={{ color: c.color }}>{t.change}</button>
            </div>
            <ul className="mt-3 space-y-2">
              {docs.length === 0 && <li className="text-[12px]" style={{ color: mut }}>—</li>}
              {docs.map((k) => (
                <li key={k}>
                  <button type="button" onClick={() => go("selfie")} className="flex w-full items-center gap-3 border p-3 text-left transition-colors"
                    style={{ borderColor: line, borderRadius: card }}>
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl" style={{ background: tint, color: c.color }}><Ic d={DOC_ICON[k]} className="h-5 w-5" /></span>
                    <span className="min-w-0 flex-1"><span className="block text-[13px] font-semibold">{t[k]}</span><span className="block text-[11px]" style={{ color: mut }}>{t[`${k}S` as "idS"]}</span></span>
                    <Ic d="M9 6l6 6-6 6" className="h-4 w-4 opacity-50" />
                  </button>
                </li>
              ))}
            </ul>
            <div className="mt-auto">
              <p className="mb-2 flex items-center justify-center gap-1.5 text-center text-[10px]" style={{ color: mut }}><Ic d="M12 3l7 3v5c0 4.500-3 8-7 10-4-2-7-5.500-7-10V6z" className="h-3 w-3" />{t.tips}</p>
              <Secured />
            </div>
          </>)}

          {step === "selfie" && (<>
            <h3 className="mt-4 text-center font-display text-[19px] font-extrabold leading-tight tracking-tight">{t.selfieT}</h3>
            <p className="mt-1 text-center text-[12px]" style={{ color: mut }}>{t.selfieS}</p>
            <div className="relative mx-auto mt-5 grid h-[230px] w-[178px] place-items-center">
              <span className="absolute inset-0 rounded-[50%]" style={{ background: soft }} />
              <svg viewBox="0 0 178 230" className="absolute inset-0 h-full w-full animate-[spin_14s_linear_infinite]" aria-hidden>
                <ellipse cx="89" cy="115" rx="86" ry="112" fill="none" stroke={c.color} strokeWidth="3" strokeDasharray="10 9" strokeLinecap="round" />
              </svg>
              <svg viewBox="0 0 100 120" className="relative h-[150px] w-[125px] opacity-30" aria-hidden>
                <circle cx="50" cy="44" r="22" fill={tx} /><path d="M10 120c3-28 20-40 40-40s37 12 40 40z" fill={tx} />
              </svg>
            </div>
            <p className="mt-4 text-center text-[10px]" style={{ color: mut }}>{t.selfieTips}</p>
            <div className="mt-auto"><Btn onClick={() => go("done")}>{t.selfieB}</Btn><Secured /></div>
          </>)}

          {step === "done" && (<>
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <div className="relative grid h-24 w-24 place-items-center">
                <span className="absolute inset-0 rounded-full" style={{ background: tint }} />
                <span className="absolute inset-3 rounded-full" style={{ background: `${c.color}33` }} />
                <span className="relative grid h-14 w-14 place-items-center rounded-full" style={{ background: c.color, color: fg }}><Ic d="M5 12.5l4.500 4.500L19 7.500" className="h-7 w-7" /></span>
              </div>
              <h3 className="mt-5 font-display text-[21px] font-extrabold leading-tight tracking-tight">{t.doneT}</h3>
              <p className="mt-2 text-[12px] leading-snug" style={{ color: mut }}>{t.doneS}</p>
              {c.redirect && <p className="mt-3 text-[10px]" style={{ color: mut }}>{t.redirect}</p>}
            </div>
            <Btn onClick={() => go("welcome")}>{t.back} {name}</Btn>
            {isMail(c.support) && <p className="mt-2 break-all text-center text-[9px]" style={{ color: mut }}>{t.help} {c.support}</p>}
            <Secured />
          </>)}
        </div>

        {/* browser bar */}
        <div className="mx-3 mb-2 flex shrink-0 items-center gap-2 rounded-full px-3 py-2 text-[11px]" style={{ background: soft }}>
          <Ic d="M7 11V8a5 5 0 0 1 10 0v3M6 11h12v9H6z" className="h-3 w-3 opacity-60" />
          <span className="flex-1 truncate text-center">{c.domain || "verify.yourcompany.com"}</span>
          <Ic d="M20 12a8 8 0 1 1-2.300-5.700M20 4v4h-4" className="h-3 w-3 opacity-60" />
        </div>
        <span className="mx-auto mb-1.5 block h-1 w-24 shrink-0 rounded-full" style={{ background: tx, opacity: 0.8 }} />
      </div>
    </div>
  );
}
