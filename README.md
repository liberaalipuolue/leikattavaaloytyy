# leikattavaaloytyy
 #LeikattavaaLöytyy pohjatyöt, julkaistu budjettiehdotus taulukkomuotoon

# 

1. Seikkaile budjetin numerotaulu-sivulle https://budjetti.vm.fi/indox/sisalto.jsp?year=2023&lang=fi&maindoc=/2023/tae/hallituksenEsitys/hallituksenEsitys.xml&opennode=0:1:143:&
2. kopioi HTML tablet
3. pyörittele tablet ATK:lla (esim Sublime Text editorilla) CSV-muotoon
    style="margin-left: 10px" aria-level="3"> --> momenttitaso 3
    style="margin-left: 5px" aria-level="2"> --> momenttitaso 2
    aria-level="1"> --> momenttitaso 1
    </a></span></td>
     <td class="tableContent" style="text-align: right"><span class="LihavaTeksti"> --> ,
        </a></td>
     <td class="tableContent" style="text-align: right"> --> ,
    url alku https://budjetti.vm.fi/
    <tr> 
     <td class="tableContent" style="text-align: left"> --> meno tai tulo alkuun
    span-tagit pois
    urlista momenttinumerot
    " ,momenttitaso --> ,momenttitaso (eli hipsut ja väli pois)
    </td> 
    </tr> 
    --> rivinvaihto 
    0-tason otsikkorivien koostaminen
    CSV otsikkorivi
    tallennus CSV-muotoon
    pilkkujen korjaus CSV-yhteensopivaksi (olisi voinut aiemmin tajuta)
    poistettavien momenttien momenttinumeroiden korjaaminen
    &amp; --> & urlien korjaaminen
    &nbsp; --> " " (binding space on erikoismerkki, korvaaminen normaalilla)
4. Siirrä haluamaasi taulukkoohjelmaan
   momenttipuuhun "." loppuun concat()-komennolla (koska unohtui), sarake tekstimuotoon
   eurot momenttitasoittain eri sarakkeisiin. 4 uutta saraketta "eurot 0 momenttitaso".."eurot 3 momenttitaso"
   momenttinimi 0-tasolta  momenttinimi-sarakkeeseen, momenttipuu arvoksi 0
   ehdollinen muotoilu muotoiltu kaava (=D1=A1)
   Mätsäilyä ja rivien liikuttelua.
   RIKKI: Jotkut momenttipuun viimeinen numero on korvautunut väärällä numerolla (28 tai 29 tai 30 tai 32 tai 33 tai 35), tekstissä ne on oikein.
   uusi sarake: sorttausapuri 2022+2023 yhdistelmä momenttipuista rivien sorttaukseen jälkikäteen EI TODELLINEN MOMENTTIPUU HUOM =CONCATENATE(C139;E139;)
