# Mudelitehas Beta: paigaldus ja avalik kataloog

Pluginapakett **0.1.1-beta.1** sisaldab kontrollitud **0.1.0** töötlusmootorit ja selle viimast jalutava mängukaru näidist. Mootori ja mudeli versioonid on eraldi: mudeli faile pole selle pakendimuudatusega uuesti genereeritud.

## Beetatest GitHubi allikast

Toetatud Codexi/töölauakeskkonnas lisa allikas:

```bash
codex plugin marketplace add orogdor/blender-cloud-test --ref v0.1.1-beta.1
```

Vali seejärel ChatGPT töölauarakenduse pluginavalikus allikaks **Mudelitehas Beta** ja paigalda **Mudelitehas Beta**. Kui käsk või allikavalik sinu kliendis puudub, ära eelda, et paigaldus õnnestus: see juhis vajab kohalikke pluginakatalooge toetavat klienti. See ei avalda pluginat universaalsesse kataloogi. GitHubi kaudu lisamist ei ole selle paketi kontrollis kasutaja töölauakliendis läbi proovitud.

Esimene proovikäsk: `Loo Mudelitehasega kontrollitud 10 000 nelinurgaga jalutav mängukaru.` Oskus peab kontrollima keskkonda ning kasutama pakis olevat karuretsepti. Käivitamiseks on vaja Blenderit 4.5.3, Python 3.12 sõltuvusi ja Blenderi Pythonile sobivat Pillow'd. Linux x64 paigaldaja asub `skills/mudelitehas/scripts/install_runtime.py`; täpne töötluskäsk on põhijuhendis. Paigaldamine ei lisa telefonile Blenderit ega käivita eraldi pilveserverit.

## Avalikku OpenAI pluginakataloogi esitamine

1. Laadi GitHubi väljalaskest alla **Mudelitehas-0.1.1-beta.1-plugin.zip**. Selles peab `plugin.json` asuma ZIP-i juures, koos `skills/` ja `assets/` kaustadega. Ära laadi selle asemel üles kogu lähtekoodi ega `-skill.zip` faili.
2. Ava https://platform.openai.com/plugins ning vali õige organisatsioon/projekt. Vajalik on kinnitatud arendaja identiteet ja avaldamisõigus. Avaldajanimi `orogdor` on GitHubi projekti nimi; portaali kinnitatud identiteedi nimi peab olema tõene ning vajadusel tuleb paketi `author.name` ja `developerName` enne esitamist sellega kooskõlla viia.
3. Vali **Upload new or existing plugin**, laadi ZIP üles ning kontrolli **Metadata & Skills** tulemusi. See on ainult oskustega pakett: MCP serverit, domeenikinnitust ega OAuthi pole deklareeritud.
4. Paranda portaali leitud vead, vajadusel asenda kirjeldus/avaldajainfo ning laadi parandatud uus versioon üles. Kohalik kontroll ei asenda OpenAI kontrolle ega kinnita kategooria või konto sobivust.
5. Täida nõutavad kinnitused ja saada kontrolli. Pärast heakskiitu vali **Publish plugin**. Paketi loomine või GitHubi väljalase ei tähenda, et see samm oleks juba tehtud.

## Kontrollimiseks sobivad näited

- Loo toetatud karu tühja töökataloogi ning kontrolli punktipilve, 10 000 nelinurgaga põhikeha, rig'i, GLB animatsiooni ja aruandeid.
- Jätka sama tööd; kontrolli vahemälu korduskasutust ja versiooniga töömanifesti.
- Koosta kaadri 0 kohta kohalik tagasisidepakett. Kontrolli, et kaader säilib ning veateadet ei saadeta automaatselt.
- Küsi 5000 nelinurgaga koera: oskus peab selgitama, et see retsept puudub, ega tohi anda karu koera pähe.

Kaasasolev pilt on tegeliku viimase karumudeli renderdus. Avaliku kataloogi heakskiitu, paigaldust kasutaja kontol ega kõigi kliendikeskkondade tuge pole väidetud.

Ametlikud juhendid: https://developers.openai.com/plugins/build/plugins ja https://developers.openai.com/plugins/deploy/submission
