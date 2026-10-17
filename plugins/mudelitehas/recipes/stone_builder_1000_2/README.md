# Mudelitehas 1000/2 — kiviaja ehitaja retsept (uus, katsetatav)

**Tellimus:** `Mudelitehas 1000 2 kiviaja ehitaja`.

See on eraldi, sisendit nõudev **retsept**, mitte valmis või sertifitseeritud mudel. Retsept ei võta V50 3D-inimest sisendiks ega teisenda vana kolmnurkmudelit tagasi „õigeks Mudelitehase mudeliks”. Inimese lähtekuju peab tulema kontrollitud T-poosis võrdluspiltidest.

## Vajalikud päris lähteandmed

- Kiviaja ehitaja idee-/tegevuspilt, sama inimese **ees-, paremalt küljelt, pealtvaate** neutraalsed T-poosi pildid. Soovitatavalt ka tagantvaade (sama identiteet, mittekopipeegeldus).
- Iga vaate jaoks eraldi mustvalge siluetimask (valge = inimfiguur; must = taust).
- Kõigi piltide ja maskide tegelikud SHA-256 räsid; piltide registreerimine meetrites (pikslit meetri kohta, pikslikoordinaatide nullpunkt, vähemalt 3 ülevaadatud tunnusmärki igas vaates).
- Ülevaatusmanifest, kus pädev ülevaataja kinnitab identiteedi, T-poosi, skaalad ja lahutatud jäsemed; **failinime või JSON-i automaatne täitmine ei tõesta ülevaatust**.

Sisendi mall on `examples/reference_manifest.example.json`. Selle `false`, `pending`, tühjad räsid ja tunnusmärgid tuleb täita **ainult tegeliku kontrolli järel**. `source_type=reviewed_generated` tähistab kontrollitud AI-pilti ja ei ole fotogramm-meetrias mõõdetud punkt.

## Paigaldus

Töökataloog peab paiknema töövoost eraldi. Retsept töötab koos Mudelitehas 0.1.2 (`plugins/mudelitehas/skills/mudelitehas/scripts/check_multiview.py`) kontrollijaga. Väljavõetava ZIP-i sees on sama kontrollija koopiana `vendor/check_multiview.py`.

Paigalda süsteemi-Pythonisse `numpy`, `Pillow`, `scipy`. **Blender 4.5.3** on vajalik päris nelinurkvõrguks, skinninguks ja GLB ekspordiks.

```bash
python -m pip install numpy scipy Pillow
python recipe/run.py --manifest /tee/kontrollitud/manifest.json --workdir /tee/uus-tookataloog --cloud-only
python recipe/run.py --manifest /tee/kontrollitud/manifest.json --workdir /tee/uus-tookataloog --blender /tee/blender-4.5.3/blender
```

Nii töötavad sammud:

1. **Pildikontroll**: kontrollib vähemalt kolme sõltumatut projektsioonisuunda, vastavad siluetimaskid, räsid, skaala, tunnusmärkide kirjed ja ülevaataja deklaratsiooni.
2. **Punktipilv enne meshi**: lõikab front/side/top siluetiruumalad kolmes mõõtmes ning salvestab `cloud_before_mesh.npz`, `calibration.json`, per-point witness'id, siluetipõhised residual'id ja `occupied_volume.npz`.
3. **Sõltumatu kontroll**: käivitab Mudelitehase päris `check_multiview.py` kontrollija. Näitab konfliktseid punkte ega sega siluetitoetust päris tunnuspunktide vastavusega. Kõigi varjatud kohtade sügavus on **hinnang**.
4. **Blenderi retopoloogia**: sobitab keha ristlõiked punktipilvele, sulatab kattuvad kehaosad üheks kestaks (`voxel_remesh`) ja teeb Blenderi QuadriFlow'ga all-quad retopo. Kontrollib ühendatust, suletust ja eelarvet.
5. **Rig ja animatsioonid**: T-poosi luustik, nahastamine ning `Idle_Loop`, `Walk_Loop`, `Build_Loop`.
6. **Eksport + kontroll**: `StoneBuilder_1000_2.blend`, `StoneBuilder_1000_2.glb`, tegelikud 4 suuna renderid, arvestus, reimporditud GLB skinning ja animatsioonide nimed.

**Kõva piirang:** kogu mudeli lähtevõrk **kuni 1000 puhast nelinurka, sealhulgas 12-quad kivikirves**. Kui Blender teeb üle eelarve, ebakorrektse nelinurga või katkise põhikeha, töövoog peatub. GLB on mängumootorisse eksportimisel kolmnurkadeks jagatud; BLEND on nelinurkne lähtefail.

## Testid (EI genereeri valmis 3D-mudelit)

```bash
python -m unittest discover -s tests -v
```

Testid tekitavad **selgelt sünteetilise ühiktesti maskid** ja kontrollivad, et puuduva kolmanda vaate, rikutud räsi, kinnitamata ülevaatuse või testandmete korral tootmismudelit ei väljastataks. Ühiktesti pildid ei ole sobilikud tootmismudeli jaoks. Positiivne unit-test kontrollib ainult punktipilve ja kolmesuunalist tunnistajaaruannet, mitte esteetikat.

## Piirangud ja järgmine samm

- Retsepti tegelik Blender 4.5.3 lõpust-lõpuni jooks nõuab päriselt üle vaadatud võrdluspilte. Ilma nendeta ei saa kasutusvalmis 1000-quad ehitajat ausalt välja anda.
- Ristlõigete syvaproportsioonid on anatoomiast tuletatud prior'id, mitte mõõdetud sügavus. Peidetud geomeetria ja liigeseasendid tuleb üle vaadata.
- 3D-mudeli võrgu kvaliteet ja tegelikud 4-vaate/renderanimatsioonid tuleb inimese poolt hinnata pärast Blenderi jooksu. Automaatne geomeetria kontroll ei tõesta visuaalset kvaliteeti ega referentspiltide identsust.
- Mängu V50 vanu mudeleid see retsept **automaatselt ei vaheta**. Kinnitatud GLB tuleb hiljem mängu varaloendurisse lisada.

Lähtestandardi allikad: [Mudelitehas SKILL.md](https://github.com/orogdor/blender-cloud-test/blob/main/plugins/mudelitehas/skills/mudelitehas/SKILL.md), `references/three-view-policy.md` ja `scripts/check_multiview.py`.
