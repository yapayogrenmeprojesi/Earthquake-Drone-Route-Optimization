# MIT License
# Copyright (c) 2025 Faruk
# Bu yazılımın kullanımına, değiştirilmesine ve dağıtılmasına izin verilir.
# Detaylar için LICENSE dosyasına bakınız.

"""Deprem bölgesinde drone ile yardım dağıtımı için küme ve rota çıkarımı.

Adımlar:

1. İhtiyaç noktaları arası mesafe matrisi ve talep tablosu okunuyor.
2. Elbow yöntemiyle küme sayısına bakılıp K-Means ile noktalar kümeleniyor.
3. Her küme, kendisine ortalama olarak daha yakın olan depoya bağlanıyor.
4. Küme içindeki noktalar Clarke-Wright tasarruf yöntemiyle drone kapasitesine
   sığacak turlara bölünüyor; her turun ziyaret sırası 2-opt ile iyileştiriliyor.
5. Grafikler ve rota listesi cikti/ klasörüne yazılıyor.

    python drone_rota.py
    python drone_rota.py --kume-sayisi 6 --kapasite 25
"""

import argparse
import os

import matplotlib

matplotlib.use("Agg")  # grafikler pencere açmadan doğrudan dosyaya yazılıyor

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.cluster import KMeans  # noqa: E402
from sklearn.manifold import MDS  # noqa: E402

KOK = os.path.dirname(os.path.abspath(__file__))
VERI_KLASORU = os.path.join(KOK, "veri")
CIKTI_KLASORU = os.path.join(KOK, "cikti")

DEPOLAR = ["Kuzey Depo", "Güney Depo"]
TALEP_SUTUNU = "Toplam Talep"
RASTGELE_TOHUM = 42

KUME_RENKLERI = ["red", "blue", "green", "purple", "orange",
                 "brown", "olive", "teal", "magenta"]
TUR_RENKLERI = ["red", "blue", "green", "purple", "orange",
                "brown", "olive", "teal", "magenta"]


def veriyi_yukle():
    """Talep tablosunu ve mesafe matrisini okur.

    Mesafe matrisinin ilk iki satırı depolara ait; geri kalanı ihtiyaç
    noktaları ve sırası talep tablosuyla aynı olmak zorunda değil, o yüzden
    talep tablosu matrisin sırasına göre yeniden diziliyor.
    """
    talepler = pd.read_excel(os.path.join(VERI_KLASORU, "yardim_talepleri.xlsx"))
    talepler = talepler.set_index("İhtiyaç Noktaları")

    mesafe = pd.read_excel(os.path.join(VERI_KLASORU, "ihtiyac_noktalari.xlsx"),
                           index_col=0)

    eksik = [depo for depo in DEPOLAR if depo not in mesafe.index]
    if eksik:
        raise SystemExit(f"Mesafe matrisinde depo satiri yok: {eksik}")

    noktalar = [ad for ad in mesafe.index if ad not in DEPOLAR]
    kayip = [ad for ad in noktalar if ad not in talepler.index]
    if kayip:
        raise SystemExit(f"Talep tablosunda karsiligi olmayan nokta: {kayip}")

    return talepler.loc[noktalar], mesafe


def elbow_grafigi(mesafe, noktalar, azami_k=9):
    """Küme sayısına karar vermek için WCSS eğrisini çizer ve kaydeder.

    K-Means, noktaların koordinatları yerine mesafe matrisindeki satırları
    üzerinde çalışıyor: her nokta, diğer bütün noktalara olan uzaklıklarından
    oluşan bir vektörle temsil ediliyor.
    """
    wcss = []
    for k in range(1, azami_k + 1):
        kmeans = KMeans(n_clusters=k, init="k-means++",
                        random_state=RASTGELE_TOHUM, n_init="auto")
        kmeans.fit(mesafe.loc[noktalar, noktalar])
        wcss.append(kmeans.inertia_)

    plt.figure(figsize=(7, 5))
    plt.plot(range(1, azami_k + 1), wcss, marker="o")
    plt.title("Elbow yöntemi")
    plt.xlabel("Küme sayısı")
    plt.ylabel("WCSS")
    plt.grid(True)
    plt.savefig(os.path.join(CIKTI_KLASORU, "elbow_metodu.png"), dpi=120,
                bbox_inches="tight")
    plt.close()
    return wcss


def kumele(mesafe, noktalar, kume_sayisi):
    kmeans = KMeans(n_clusters=kume_sayisi, init="k-means++",
                    random_state=RASTGELE_TOHUM, n_init="auto")
    return kmeans.fit_predict(mesafe.loc[noktalar, noktalar])


def koordinatlari_cikar(mesafe):
    """Mesafe matrisinden çizim için iki boyutlu koordinat üretir.

    MDS yalnızca grafikler içindir; bütün mesafe hesapları matrisin kendisi
    üzerinden yapılıyor, çünkü MDS düzleme indirirken hata payı bırakıyor.
    """
    mds = MDS(n_components=2, dissimilarity="precomputed",
              random_state=RASTGELE_TOHUM, normalized_stress="auto")
    yerlesim = mds.fit_transform(mesafe)
    return pd.DataFrame(yerlesim, index=mesafe.index, columns=["X", "Y"])


def depo_ata(mesafe, kume_noktalari):
    """Kümeyi, noktalarına ortalamada daha yakın olan depoya bağlar.

    Eski sürümde küme numarasına bakılıp depo elle veriliyordu (0 ve 3 kuzey,
    diğerleri güney). Küme sayısı ya da tohum değişince o eşleme bozuluyordu.
    """
    ortalamalar = {depo: mesafe.loc[depo, kume_noktalari].mean() for depo in DEPOLAR}
    return min(ortalamalar, key=ortalamalar.get)


def tur_uzunlugu(tur, depo, mesafe):
    """Depodan çıkıp turu gezip depoya dönen yolun uzunluğu."""
    yol = [depo] + list(tur) + [depo]
    return sum(mesafe.at[yol[i], yol[i + 1]] for i in range(len(yol) - 1))


def iki_opt(tur, depo, mesafe):
    """Turu 2-opt ile iyileştirir: kesişen iki kenarı ters çevirerek kısaltır."""
    en_iyi = list(tur)
    en_iyi_uzunluk = tur_uzunlugu(en_iyi, depo, mesafe)

    gelisme_var = True
    while gelisme_var:
        gelisme_var = False
        for i in range(len(en_iyi) - 1):
            for j in range(i + 1, len(en_iyi)):
                aday = en_iyi[:i] + en_iyi[i:j + 1][::-1] + en_iyi[j + 1:]
                aday_uzunluk = tur_uzunlugu(aday, depo, mesafe)
                if aday_uzunluk < en_iyi_uzunluk - 1e-9:
                    en_iyi, en_iyi_uzunluk = aday, aday_uzunluk
                    gelisme_var = True
    return en_iyi


def turlari_kur(noktalar, talep, depo, mesafe, kapasite):
    """Küme noktalarını drone kapasitesine sığan turlara böler.

    Clarke-Wright tasarruf yöntemi kullanılıyor. Başlangıçta her nokta kendi
    başına bir tur; iki turu birleştirmenin kazandırdığı yol

        tasarruf(i, j) = d(depo, i) + d(depo, j) - d(i, j)

    ile hesaplanıp en çok kazandıran birleştirmeden başlanıyor. Kapasiteyi
    aşmayan ve iki turun uçlarını birbirine bağlayan birleştirmeler kabul
    ediliyor. Sonunda her tur ayrıca 2-opt ile iyileştiriliyor.

    Sadece "en yakın noktayı al" demek yetmiyordu: kapasiteye sığan en yakın
    nokta seçilince turlarda küçük boşluklar kalıyor ve gereksiz yere fazladan
    tur açılıyordu. Tasarruf yöntemi hem daha az tur hem daha kısa yol çıkarıyor.
    """
    buyuk = [n for n in noktalar if talep[n] > kapasite]
    if buyuk:
        raise SystemExit(
            f"Tek basina kapasiteyi asan nokta var (kapasite {kapasite}): {buyuk}"
        )

    turlar = {no: [nokta] for no, nokta in enumerate(noktalar)}
    yukler = {no: talep[nokta] for no, nokta in enumerate(noktalar)}
    tur_no = {nokta: no for no, nokta in enumerate(noktalar)}

    tasarruflar = []
    for a in range(len(noktalar)):
        for b in range(a + 1, len(noktalar)):
            i, j = noktalar[a], noktalar[b]
            tasarruflar.append(
                (mesafe.at[depo, i] + mesafe.at[depo, j] - mesafe.at[i, j], i, j)
            )
    tasarruflar.sort(key=lambda satir: -satir[0])

    for tasarruf, i, j in tasarruflar:
        if tasarruf <= 0:
            break  # birlestirmek yolu uzatiyorsa gerisine bakmaya gerek yok

        ilk_no, ikinci_no = tur_no[i], tur_no[j]
        if ilk_no == ikinci_no:
            continue
        if yukler[ilk_no] + yukler[ikinci_no] > kapasite:
            continue

        ilk, ikinci = turlar[ilk_no], turlar[ikinci_no]

        # i birinci turun sonunda, j ikinci turun basinda olmali; mesafeler
        # simetrik oldugu icin gerekirse turlari ters cevirebiliyoruz.
        if ilk[0] == i:
            ilk = ilk[::-1]
        elif ilk[-1] != i:
            continue
        if ikinci[-1] == j:
            ikinci = ikinci[::-1]
        elif ikinci[0] != j:
            continue

        turlar[ilk_no] = ilk + ikinci
        yukler[ilk_no] += yukler[ikinci_no]
        for nokta in ikinci:
            tur_no[nokta] = ilk_no
        del turlar[ikinci_no], yukler[ikinci_no]

    return [iki_opt(tur, depo, mesafe) for tur in turlar.values()]


def sirali_turlar(noktalar, talep, kapasite):
    """Karşılaştırma için: noktaları tablodaki sırayla kapasiteye böler.

    Eski sürümün yaptığı buydu; mesafeye hiç bakmadan sıradaki noktayı alıp
    kapasite dolunca yeni tura geçiyordu.
    """
    turlar = []
    tur = []
    yuk = 0
    for nokta in noktalar:
        if yuk + talep[nokta] <= kapasite:
            tur.append(nokta)
            yuk += talep[nokta]
        else:
            turlar.append(tur)
            tur = [nokta]
            yuk = talep[nokta]
    if tur:
        turlar.append(tur)
    return turlar


def genel_grafik(talepler, yerlesim, kume_sayisi):
    """Bütün kümeleri ve iki depoyu tek grafikte gösterir."""
    plt.figure(figsize=(9, 7))

    for kume_no in range(kume_sayisi):
        kume = talepler[talepler["Kume"] == kume_no]
        renk = KUME_RENKLERI[kume_no % len(KUME_RENKLERI)]
        plt.scatter(yerlesim.loc[kume.index, "X"], yerlesim.loc[kume.index, "Y"],
                    s=90, color=renk, label=f"Küme {kume_no}")
        for ad in kume.index:
            plt.text(yerlesim.at[ad, "X"], yerlesim.at[ad, "Y"],
                     str(talepler.at[ad, "Nokta Adı"]), fontsize=8, ha="right")

    for depo in DEPOLAR:
        plt.scatter(yerlesim.at[depo, "X"], yerlesim.at[depo, "Y"],
                    s=220, c="black", marker="X", label=depo)

    plt.title("Kümeler ve depolar")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
    plt.grid(True)
    plt.savefig(os.path.join(CIKTI_KLASORU, "kumeler_ve_depolar.png"), dpi=120,
                bbox_inches="tight")
    plt.close()


def kume_grafigi(talepler, yerlesim, kume_no):
    """Tek bir kümenin noktalarını ve iki depoyu çizer."""
    kume = talepler[talepler["Kume"] == kume_no]
    renk = KUME_RENKLERI[kume_no % len(KUME_RENKLERI)]

    plt.figure(figsize=(8, 6))
    plt.scatter(yerlesim.loc[kume.index, "X"], yerlesim.loc[kume.index, "Y"],
                s=90, color=renk, label=f"Küme {kume_no}")
    for ad in kume.index:
        plt.text(yerlesim.at[ad, "X"], yerlesim.at[ad, "Y"],
                 str(talepler.at[ad, "Nokta Adı"]), fontsize=8, ha="right")

    for depo in DEPOLAR:
        plt.scatter(yerlesim.at[depo, "X"], yerlesim.at[depo, "Y"],
                    s=220, c="black", marker="X", label=depo)

    plt.title(f"Küme {kume_no} - ihtiyaç noktaları")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
    plt.grid(True)
    plt.savefig(os.path.join(CIKTI_KLASORU, f"kume_{kume_no}_noktalar.png"),
                dpi=120, bbox_inches="tight")
    plt.close()


def rota_grafigi(talepler, yerlesim, kume_no, depo, turlar, ilk_drone_no):
    """Bir kümenin drone turlarını depodan başlayıp depoya dönecek şekilde çizer."""
    plt.figure(figsize=(9, 7))

    for sira, tur in enumerate(turlar):
        yol = [depo] + list(tur) + [depo]
        renk = TUR_RENKLERI[sira % len(TUR_RENKLERI)]
        plt.plot(yerlesim.loc[yol, "X"], yerlesim.loc[yol, "Y"],
                 linestyle="--", color=renk, label=f"Drone {ilk_drone_no + sira}")

    kume = talepler[talepler["Kume"] == kume_no]
    plt.scatter(yerlesim.loc[kume.index, "X"], yerlesim.loc[kume.index, "Y"],
                s=90, color="black")
    for ad in kume.index:
        plt.text(yerlesim.at[ad, "X"], yerlesim.at[ad, "Y"],
                 f"{talepler.at[ad, 'Nokta Adı']} ({talepler.at[ad, TALEP_SUTUNU]} birim)",
                 fontsize=8, ha="right")

    plt.scatter(yerlesim.at[depo, "X"], yerlesim.at[depo, "Y"],
                s=220, c="black", marker="X", label=depo)

    plt.title(f"Küme {kume_no} - drone rotaları ({depo})")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
    plt.grid(True)
    plt.savefig(os.path.join(CIKTI_KLASORU, f"kume_{kume_no}_rota.png"), dpi=120,
                bbox_inches="tight")
    plt.close()


def main():
    ayristirici = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ayristirici.add_argument("--kume-sayisi", type=int, default=5,
                             help="K-Means küme sayısı (varsayılan: 5)")
    ayristirici.add_argument("--kapasite", type=int, default=30,
                             help="bir dronun taşıyabileceği azami birim (varsayılan: 30)")
    secenekler = ayristirici.parse_args()

    os.makedirs(CIKTI_KLASORU, exist_ok=True)

    talepler, mesafe = veriyi_yukle()
    noktalar = list(talepler.index)
    talep = talepler[TALEP_SUTUNU]

    elbow_grafigi(mesafe, noktalar)
    talepler = talepler.copy()
    talepler["Kume"] = kumele(mesafe, noktalar, secenekler.kume_sayisi)

    yerlesim = koordinatlari_cikar(mesafe)
    genel_grafik(talepler, yerlesim, secenekler.kume_sayisi)

    satirlar = []
    ziyaret_edilen = []
    toplam_mesafe = 0.0
    sirali_mesafe = 0.0
    drone_no = 1

    for kume_no in range(secenekler.kume_sayisi):
        kume_noktalari = list(talepler.index[talepler["Kume"] == kume_no])
        if not kume_noktalari:
            continue

        depo = depo_ata(mesafe, kume_noktalari)
        turlar = turlari_kur(kume_noktalari, talep, depo, mesafe, secenekler.kapasite)

        kume_grafigi(talepler, yerlesim, kume_no)
        rota_grafigi(talepler, yerlesim, kume_no, depo, turlar, drone_no)

        for tur in sirali_turlar(kume_noktalari, talep, secenekler.kapasite):
            sirali_mesafe += tur_uzunlugu(tur, depo, mesafe)

        for tur in turlar:
            ziyaret_edilen.extend(tur)
            uzunluk = tur_uzunlugu(tur, depo, mesafe)
            toplam_mesafe += uzunluk
            duraklar = " -> ".join(
                f"Nokta {talepler.at[ad, 'Nokta Adı']} ({talep[ad]} birim)"
                for ad in tur
            )
            satirlar.append({
                "Kume": kume_no,
                "Drone": drone_no,
                "Depo": depo,
                "Yuk": int(talep[tur].sum()),
                "Mesafe": round(uzunluk, 2),
                "Rota": f"{depo} -> {duraklar} -> {depo}",
            })
            drone_no += 1

        print(f"Kume {kume_no}: {len(kume_noktalari)} nokta, {depo}, "
              f"{len(turlar)} drone turu")

    # Her nokta tam olarak bir dronun rotasında geçmeli
    if sorted(ziyaret_edilen) != sorted(noktalar):
        eksik = set(noktalar) - set(ziyaret_edilen)
        fazla = [ad for ad in set(ziyaret_edilen) if ziyaret_edilen.count(ad) > 1]
        raise SystemExit(f"Rotalar tutarsiz. Ziyaret edilmeyen: {eksik}, "
                         f"birden fazla ziyaret edilen: {fazla}")

    rotalar = pd.DataFrame(satirlar)
    csv_yolu = os.path.join(CIKTI_KLASORU, "drone_rotalari.csv")
    rotalar.to_csv(csv_yolu, index=False, encoding="utf-8-sig")

    print()
    print(f"Toplam tur sayisi: {len(rotalar)}")
    print(f"Tasinan toplam yuk: {int(talep.sum())} birim")
    print(f"Toplam mesafe: {toplam_mesafe:.1f}")
    print(f"Sadece tablo sirasiyla gidilseydi: {sirali_mesafe:.1f}")
    if sirali_mesafe > 0:
        kazanc = 100 * (sirali_mesafe - toplam_mesafe) / sirali_mesafe
        print(f"Kazanc: yuzde {kazanc:.1f}")
    print(f"Ciktilar: {os.path.relpath(CIKTI_KLASORU, KOK)}")


if __name__ == "__main__":
    main()
