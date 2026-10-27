# ModelFactory Stage 2A — esialgne punktipilv

- 166 310 tegelikku 3D-punkti PLY-vormingus.
- Alus: kohalikud SDXL-i neljavaatekatse pildid. Eestvaate siluett määrab kõrguse ja laiuse; tagantvaade annab osalise tagatekstuuri.
- Sügavus on anatoomilise priori abil oletatud, sest AI genereeritud külgvaated ei olnud tegelikud külgprojektsioonid.
- Eeldatud inimfiguuri pikkus 1,78 m. Eest/tagant joondatud siluettide IoU ligikaudu 0,673.
- PLY atribuudid: x, y, z, RGB, source (front=0, back=1, inference=2), confidence.
- ZIP sisaldab binaarset PLY-d, Pythoni rekonstruktsiooniskripti, QC-vaateid, manifesti ja eestikeelset raportit.
- Tulemus ei ole veel korrektne 3D-inimene ega mesh; sügavus ja rõivad vajavad parandamist. Punkt 2B ei ole alustatud.
