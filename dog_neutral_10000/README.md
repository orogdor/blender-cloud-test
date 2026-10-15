# Mudelitehas 10000 3 sitsiv koer

Uus katse: tellitud sitsiv 2D-pilt -> sama koera seisev nelivaade ->
joondatud pildimaskid ja hinnatud anatoomiline sügavus -> päris salvestatud
punktipilv -> Poissoni pind -> täpselt 10 000 nelinurgaga põhikeha -> luustik
ehituspoosis -> luustikuanimatsiooniga sitsima ja tagasi.

Lähtepiltidel on sama kuldpruun koer heleda koonu/rinnaga ja lontis kõrvadega.
Nelivaate pikslid on päriselt üle vaadatud; manifest on ülevaatuse kirje,
mitte automaatne pilditõlgendaja. Pildid ei ole skaneering ega kalibreeritud
fotod: jäsemete varjatud sügavus, liigeste keskmed ja tegelik mõõtkava on hinnang.

`prepare.py` registreerib nelivaate. Nelja paneeli piirid valitakse nähtava
valge eraldusruumi järgi, sest pildi tükeldamine neljaks võrdseks ristkülikuks
lõikaks profiili koonu või saba maha. Materjali allikad säilitavad peene karva.

`reconstruct.py` salvestab esmalt orienteeritud punktipilve, seejärel loob
Poissoni meshi. Ümarad anatoomilised ristlõiked on pildimaskidega piiratud
sügavushinnangud. Punktid ei ole võetud olemasolevalt 3D-mudelilt.

`build.py` loob 10 000 nelinurgaga kinnise põhikeha, UV/PBR kaardid,
neljajalgse luustiku ja animatsiooni. Tagakäppade kontakt hoitakse kahe luu
kinemaatikaga paigal. Seismise ja sitsimise vahel ei ehitata keha ümber ega
asendata seda teise mudeliga. Silmade/nina/suu detailid lisanduvad geomeetria
arvestusele eraldi. LOD eksport on väiksema mahuga.

Pärandretseptist `dog_mudelitehas/build_dog.py` taaskasutatakse üksnes
topoloogia kontrolli, täpse ruutude arvu paranduse ja ekspordi abifunktsioone.
Selle vana poseeritud koera geomeetriat, luustikku ega animatsiooni ei kasutata.

Käivitamine GitHub Actionsis: `Mudelitehas - Tase 3 - Koer 10000 neutraalpoosist`.
Allikapildid on `assets.b85` ZIP-pakis; töövoog pakib need enne ehitamist lahti.
`rest_inputs.b85` sisaldab registreeritud vaateid ja maske. Kontrollitakse
meshi kinnisust, nelinurkade arvu, deformatsiooni, luude pikkusi,
tagakäppade kontakti, nelja vaate kattuvust ja GLB animatsiooni olemasolu.
Eneselõikumiste kontroll hõlmab lisaks arvudele tegeliku mudeli vaadete ülevaatust;
see ei ole täielik kõikide kolmnurkade kokkupõrgete matemaatiline tõestus.
