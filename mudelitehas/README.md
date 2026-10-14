# Mudelitehas: kolm taset

Vestluse ühine käsuvorm:

```text
Mudelitehas <nelinurkade arv> <tase> <mudeli kirjeldus>
```

Näide `Mudelitehas 5000 1 karu` tähendab: loo 5000 nelinurgaga karu tasemel 1.
Näidiskäsu mainimine juhendi arutamisel ei käivita uut mudelit.

| Tase | Nimi | Sisu |
|---|---|---|
| 1 | Kiire | Lihtne kinnine mesh, üks põhivärv, GLB/BLEND ja kiire eelvaade. Põhiretsept on staatiline. |
| 2 | Tavaline | Varasema karutesti töövoog: täpsem rekonstruktsioon, pildipõhine värv; luustik ja animatsioon, kui tellitud ja mudelile sobivad. |
| 3 | Täiustatud | Uue koeratesti töövoog: kuju sügavushinnangud, UV/PBR, vajalikud eraldi detailid, deformatsiooni kontroll, LOD ja vaadete võrdlus. Luustik ja animatsioon vastavalt tellimusele. |

Kõigi tasemete põhijada on sama: **2D-pilt → neli vaadet → punktipilv → mesh**.
Luustik ja animatsioon lisanduvad vastavalt tellimusele. Tase määrab töötlemise põhjalikkuse; nelinurkade arv määrab põhikeha geomeetria mahu.
Tase 3 ei taga automaatselt fotorealismi. Peened ja varjatud kujundid vajavad head lähtematerjali ning kuju kontrolli.

## Käsunäited

```text
Mudelitehas 5000 1 karu
Mudelitehas 20000 2 karu jooksuanimatsiooniga
Mudelitehas 100000 3 sitsiv koer animatsiooniga
Mudelitehas 10000 3 ralliauto
```

Viimane osa võib olla mitmesõnaline kirjeldus. Animatsiooniga tellimuses tuleb kirjeldada liikumist; lihtsalt “animatsiooniga” puhul valib vestluses assistent kirjeldatud poosile sobiva lihtsa tegevuse.
Arv tähendab põhimeshi nelinurki, mitte GLB kolmnurki. GLB trianguleerib nelinurgad; tase 3 võib lisada silmade, karvade ja muude detailide geomeetriat. Kõik koguarvud esitatakse kontrolliaruandes.

## Mis on praegu käivitatav?

- `command.py` tõlgendab kõigi kolme taseme käske ja koostab ühtse tellimuse JSON-i. See ei genereeri ise pilte ega muuda faile ilma `--output` argumendita.
- `profiles.json` määrab tasemete nõuded.
- Taseme 1 uus GitHubi töövoog loob ettevalmistatud nelja vaate andmetest lihtsa staatilise meshi. Töövoog käivitatakse käsitsi; selle lisamine või näidiskäsu kirjutamine siin ei genereeri karu.
- Taseme 2 karu- ja taseme 3 koeraretseptid on varasemad käivitatud näidised. Need ei ole universaalsed automaatsed luustiku loojad igale objektile.
- Uue objekti tellimuses loob assistent kõigepealt lähtepildi ja neli vaadet, valmistab andmed ning sobitab valitud taseme Blenderi retsepti objekti ja tellitud mahu järgi. Pelk käsutekst GitHubis ei kutsu ChatGPT pildigeneraatorit automaatselt välja.

## Parser

```bash
python3 mudelitehas/command.py "Mudelitehas 5000 1 karu" --output request.json
```

## Tase 1

GitHubi töövoog `Mudelitehas - Tase 1 - Kiire mesh` võtab käsu ja joondatud nelja vaate `.b85` andmefaili tee.
Vaikimisi allikaks on varasema karutesti neli vaadet. Teise objekti jaoks tuleb anda selle objekti ettevalmistatud andmed; kirjelduse muutmine ei muuda olemasolevaid karu lähtesiluette.
Praegune täpse nelinurkade arvu retsept toetab paarisarve alates 256-st. Taseme 1 põhiretsept ei lisa luustikku ega animatsiooni.

```bash
python3 mudelitehas/reconstruct_level1.py --input teddy_mudelitehas/teddy_inputs.b85 --request request.json
blender --background --factory-startup --python-exit-code 1 --python mudelitehas/build_level1.py -- --request request.json
```

Väljundid asuvad `output/mudelitehas_level1/` all. Punktipilv salvestatakse enne meshi loomist.
