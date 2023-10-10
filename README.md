# Tämä repo on yhdistelmä skriptejä budjetin tekemiseen
uusi_budjetti-osiossa kerrotaan CSV-muokkaukseen tarkoitetuista skripteistä.
Lisäksi Python-skriptillä voi Googlen spreadsheetistä ajaa HTML-taulukon Wordpressiin julkaistavaksi.

# uusi_budjetti
 Tämä skripti muuntaa VM:n antamat CSV:t taulukkomuotoon josta on helpompi työstää budjettia taulukko-ohjelmissa. 
 * Laskee VM:n CSV:stä puuttuvat 2. ja 1. tason momentit valmiiksi.
 * Tekee CSV:stä saatavan uuden budjetin vanhaan taulukkomuodossa olevaan budjettiin sopivaksi.

 Aarne Leinonen, ChatGPT3.5 apuna. Vapaasti vaihtoehtobudjettien tekijöiden iloksi. Liberaalipuolue - Vapaus valita 2024 vaihtoehtobudjetin nopeaa rutistusta varsinkin auttamaan. Kehitysehdotukset voi välittää pull requesteilla ja kiitokset somessa.

## Seuraa näitä vaiheita:
 0. Lataa tämän repositorion tiedostot, tai ainakin index.html ja script.js samaan kansioon tietokoneellasi ja avaa selaimella index.html-tiedosto.

## Hae Budjetti
 1. Valtiovarainministeriön sivuilta https://budjetti.vm.fi/indox/opendata-csv.jsp
 2. Esimerkiksi https://budjetti.vm.fi/indox/opendata/2024/tae/valtiovarainministerionKanta/2024-tae-valtiovarainministerionKanta.html _tai jos VM jumittaa niin https://web.archive.org/web/20231007062101/https://budjetti.vm.fi/indox/opendata/2024/tae/valtiovarainministerionKanta/2024-tae-valtiovarainministerionKanta.html ._
 3. Lataa haluamasi CSV tiedostot.
 4. Yhdistä kaikki CSV tiedostot notepadilla yhteen tiedostoon. _Vaihtoehtoisesti käytä kansiossa data olevaa "yhdistelmä budjetti TAE 2024.csv"-tiedostoa. Varmista että VM ei ole lisäillyt ylimääräisiä puolipisteitä tai muita merkkejä joilla CSV sekoaa tai tekee virheellisiä rivimittoja. Otsikkorivejä voi vähentää nyt tai taulukko-ohjelmassa._

## Avaa index.html
 5. Syötä CSV tiedosto kenttään. _Valitse Nordic (ISO 8859-10) jos käytät VM:n CSV-tiedostoa suoraan sellaisenaan. Jos puolestaan sinulla on UTF-8 enkoodattu tiedosto, niin valitse se._

## Vertaa vanhaan budjettiin
 6. Käytä edellisen vuoden budjetin "budjettipuu"-kolumnia jonka muoto on momenttitasot eroteltuna pisteillä, tyyliin "33.40.54." _Vaihtoehtoisesti käytä kansiossa data olevaa "Budjettipuu 2023.txt"-tiedostoa, joka on Liberaalipuolueen 2023 vaihtoehtobudjetin rakenne._

## Kopioi taulukko haluamaasi taulukko-ohjelmaan
 7. Kopioi HTML-sivun taulukko-osuus maalaamalla kaikki taulukon rivit ja kopioimalla ne taulukko-ohjelmaan.
 8. Luo kadonnut otsikkorivi uudelleen. _Esimerkiksi kopioimalla tämä: "Momenttitaso	Budjettipuu	Pääluokan numero	Pääluokan nimi	Menoluvun numero	Menoluvun nimi	Menomomentin numero	Menomomentin nimi	Menomomentin info-osa	Määräraha	Aiemmin budjetoitu IX lisätalousarvio 2023	Aiemmin budjetoitu VIII lisätalousarvio 2023	Aiemmin budjetoitu VII lisätalousarvio 2023	Aiemmin budjetoitu VI lisätalousarvio 2023	Aiemmin budjetoitu V lisätalousarvio 2023	Aiemmin budjetoitu IV lisätalousarvio 2023	Aiemmin budjetoitu III lisätalousarvio 2023	Aiemmin budjetoitu II lisätalousarvio 2023	Aiemmin budjetoitu I lisätalousarvio 2023	Aiemmin budjetoitu 2023	Toteutuma 2023	Toteutuma 2022"_
 8. Google Spreadsheetissä pitää muuttaa "budjettipuu"-kolumni "Pelkkä teksti" formaattiin, jotta sitä ei kohdella lukuna ja sorttaaminen oikeaan järjestykseen mahdollistuu.
 9. "Budjettipuoli"-sarake sisältönään riveittäin "tulo" tai "meno" kannattaa myös luoda.
