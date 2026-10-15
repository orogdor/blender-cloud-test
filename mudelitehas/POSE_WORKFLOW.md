# Elusolend: lõpp-poos ja ehituspoos

Uute elusolendite töövoog kõigil kolmel tasemel:

1. **2D-pilt tellitud poosis.** Näiteks koer sitsib esikäpad üleval. See määrab välimuse, identiteedi ja soovitud lõpp-poosi.
2. **Sama olendi neli vaadet ehituspoosis.** Inimene on T-poosis; koer, kass ja muu neljajalgne seisab loomulikult neljal jalal. Kehaproportsioonid, värvid ja detailid peavad jääma samaks. Käpad, käed, jalad ja saba peavad olema võimalikult eristatavad. Teistsuguse olendi puhul määratakse enne jäsemete arv ja sobiv ehituspoos.
3. **Punktipilv ehituspoosis.** Punktid tekivad nelivaate andmetest enne meshi. Siluettide ruumala ristumine vajab orgaanilisi ümaraid ristlõikeid ning detailse mudeli puhul kohalikku sügavushinnangut. Pelgalt ruumala ristumine võib tekitada lapikuid ja kandilisi jäsemeid.
4. **Mesh ehituspoosis.** Kontrollida ruumilist kuju, mitte ainult silueti kattuvust. Sobitada servade paigutus liigeste painutustega, säilitada jäsemete vahed ning kontrollida ka kaldu kontrollvaateid. Silumine ei tohi jäsemeid kokku sulatada. Smooth shading üksi ei paranda geomeetriat.
5. **Luustik ja naha mõjud ehituspoosis.** Liigeste keskmed tuletatakse nelivaate nähtavatest tunnustest ja anatoomiast. Nelja pildi põhjal ei saa kõiki peidetud liigeseid täpselt mõõta; hinnangud tuleb üles märkida. Kontrollida küünarnukke, õlgu, puusi, põlvi, kannaliigeseid ja sabaahelat.
6. **Luustiku abil tellitud poosi.** Seisev koer viiakse animatsiooniga sitsima. Keha ei ehitata juba kokku volditud jäsemetega. Luude pikkused säilivad, kontaktid põranda või esemega lahendatakse IK või mudelile sobiva poseerimisega. Lõpp-poosi võrreldakse esimese 2D-pildiga, arvestades kaamera erinevust.
7. **Väljund ja kontroll.** Säilitada redigeeritav ehituspoos ning luustik. Anda lõpp-poosis mudel, tegelik animatsioon ja sellest renderdatud eelvaade. Kontrollida eneselõikumisi, naha venimist, käppade/jalataldade kontakte ja eksporditud GLB animatsiooni.

## Miks see kandilisust vähendab?

Eraldi nähtavad jäsemed annavad paremad kuju- ja liigesehinnangud ning aitavad vältida käpa ja rindkere üheks massiks sulamist. Ümarad ristlõiked parandavad siluettidest saadava ruumala nurgelisi servi. Suurem ruutude arv, Smooth shading või Subdivision üksi ei taasta puuduvat anatoomiat. Tekstuur ja karv ei asenda õiget kehakuju.

`organic_surface.py` lisab taseme 1 punktipilve etapile komponentide kaupa elliptilise ristlõike piirangu. See on **sügavuse hinnang**, mitte mõõdetud 3D. Liigeste ja keerulise anatoomia jaoks on endiselt vaja kohalikku ülevaatust ja mudelipõhist retsepti.

## Poosiplaan ja lähteandmete kontroll

`command.py` lisab tellimusele `pose_plan` välja, milles on:

- tellitud poosi kirjeldus ja eesmärk;
- ehituspoos (`humanoid_t`, `quadruped_stand` või eraldi ülevaatust vajav kehaehitus);
- eraldi rollid lõpp-poosi pildile ja ehituspoosi nelivaatele;
- luustiku, poseerimise ja lõppkontrolli nõuded.

Nelivaatega tuleb kaasa anda kontrollmanifest. Näidis on `reference_manifest.example.json`. See peab sisaldama tegeliku `.b85` faili SHA-256 räsi ja toimunud visuaalse ülevaatuse andmeid.

Manifesti kontrollija tuvastab puuduva või vale ehituspoosi kirjelduse, vigase ülevaatuskirje ja teisele failile kuuluva räsi. **See kood ei vaata pildi piksleid ega tõesta ise, et pildil on õige poos.** Visuaalne ülevaatus tuleb päriselt teha; näidise `pending` staatust ei tohi automaatselt heakskiiduks muuta.

```bash
python3 mudelitehas/command.py "Mudelitehas 100000 3 sitsiv koer animatsiooniga" --output request.json
```

Sellise tellimuse ehituspoos on `quadruped_stand`, eesmärk `sit_pretty`. Nelivaate loomisel tuleb näidata seisvat sama koera, mitte sitsivat koera.

## Praegune teostus ja vanad näidised

- Uus käsuplaan ning taseme 1 lähteandmete kontroll rakendavad pooside eraldamist. Taseme 1 punktipilve rekonstruktsioon sisaldab orgaanilist ristlõike ümardamist.
- Taseme 1 olemasolev Blenderi baasretsept on staatiline. Elusolendi tellimust see nüüd vaikselt staatilise lõpptulemusena ei väljasta: tuleb koostada mudelile sobiv luustiku- ja poosiretsept. Sama kohustus kehtib tasemetele 2 ja 3.
- Üldist, kõigile olenditele automaatselt sobivat luustiku ja lõpp-poosi lahendajat need muudatused ei lisa. Mudelipõhised liigeste hinnangud ja poseerimine tuleb iga uue ehituspoosi lähteandmete järgi teha.
- Varasemad `teddy_mudelitehas` ja `dog_mudelitehas` on **pärandnäidised**, mis rekonstrueeriti juba poseeritud nelivaatest. Need jäävad ajaloo taasesituseks ega ole uue poosipõhimõtte jaoks sobivad lähtemallid.
- Olemasolevad GLB- ja BLEND-failid ei muutu juhendi või parseri uuendamisel. Uue meetodi visuaalset tulemust tuleb kinnitada uuesti loodud ehituspoosis mudeli ja selle poseerimisega.

Koodi kontrollid: `python3 -m unittest mudelitehas.test_pose_workflow -v`. Testid kontrollivad poosiplaani, lähtefaili ja ülevaatuskirje sidumist ning ümardamise geomeetrilisi omadusi. Need ei ole uue koeramudeli Blenderi renderdus- ega animatsioonikatsed.
