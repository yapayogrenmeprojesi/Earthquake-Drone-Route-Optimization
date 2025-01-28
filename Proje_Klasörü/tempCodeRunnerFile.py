import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from sklearn.manifold import MDS
import networkx as nx
import heapq
import os



# Verileri yüklüyoruz 
yardim_talepleri = pd.read_excel('yardim_talepleri.xlsx')  
yardim_talepleri.set_index('İhtiyaç Noktaları', inplace=True)
mesafe_matrisi = pd.read_excel('ihtiyac_noktalari.xlsx', index_col=0)

# Depoları dahil ederek mesafeleri ayarlıyoruz 
depo_sayisi = 2
depo_indexleri = list(range(depo_sayisi))  # Depo indeksleri integer olarak belirleniyoruz 

# Elbow methodunun olduğu kısım
WCSS = []
for i in range(1, 10):
    kmeans = KMeans(n_clusters=i, init='k-means++', random_state=42, n_init='auto')
    kmeans.fit(mesafe_matrisi.iloc[depo_sayisi:, depo_sayisi:])  # Depolar hariç tutularak fit edilir
    WCSS.append(kmeans.inertia_)

# Elbow grafiğini çizelim
plt.plot(range(1, 10), WCSS, marker='o')
plt.title("Elbow Methodu")
plt.xlabel("Küme Sayısı")
plt.ylabel("WCSS")
plt.show()

# Optimal küme sayısını elbow grafiğinden alıp kendimiz bu değeri manuel olarak giriyoruz.
k_optimal = 5
kmeans = KMeans(n_clusters=k_optimal, random_state=42, n_init='auto')
kume_etiketleri = kmeans.fit_predict(mesafe_matrisi.iloc[depo_sayisi:, depo_sayisi:])

# Yardım taleplerine küme etiketini atıyoruz
yardim_talepleri = yardim_talepleri[yardim_talepleri.index.isin(mesafe_matrisi.index[depo_sayisi:])]
yardim_talepleri['Kume'] = kume_etiketleri
yardim_talepleri.index = range(1, len(yardim_talepleri) + 1)

# MDS ile Koordinatları hesaplıyoruz.
mds = MDS(n_components=2, dissimilarity='precomputed', random_state=42, normalized_stress='auto')
koordinatlar = mds.fit_transform(mesafe_matrisi)
yardim_talepleri['X'] = koordinatlar[depo_sayisi:, 0]
yardim_talepleri['Y'] = koordinatlar[depo_sayisi:, 1]



def a_star(graph, start, goal):
    heap = []
    heapq.heappush(heap, (0, start))  # Başlangıç düğümüne heap'e ekliyoruz
    came_from = {}  # Başlangıçtan hangi noktaya nasıl gidildiği bilgisini tutacak
    cost_so_far = {start: 0}  # Başlangıç noktasına gidilen maliyet (başlangıçta sıfır olacak şekilde) tutacak

    while heap:
        current_cost, current = heapq.heappop(heap)  # En düşük maliyetli düğümü seçer

        if current == goal:
            # Amaç düğümüne ulaşıldığında yolu takip eder
            path = []
            while current is not None:
                path.append(current)
                current = came_from.get(current)  # Daha önceki düğümü takip eder
            return path[::-1]  # Yolu tersten sıralayarak döndürür.
        
        for neighbor in graph.neighbors(current):
            # Komşu düğümlere ait ağırlıkları alır
            # 'weight' burada kenarın (edge) ağırlığını temsil eder (yani mesafeyi)
            if graph[current][neighbor].get('weight') is None:
                # Eğer kenarda bir 'weight' (mesafe) yoksa bir varsayılan değer kullanabiliriz
                # Örneğin, 1 olarak kabul edebiliriz
                new_cost = cost_so_far[current] + 1
            else:
                new_cost = cost_so_far[current] + graph[current][neighbor]['weight']  # Kenarın ağırlığını ekliyoruz

            # Eğer yeni maliyet daha küçükse, ilgili bilgiyi güncelliyoruz
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost
                heapq.heappush(heap, (priority, neighbor))  # Daha düşük maliyetli komşuyu heap'e eklenir
                came_from[neighbor] = current  # Komşuyu current'tan gelerek ziyaret ettiğimizin bilgisini tutar
    return None  




def dron_gorsel_a_star(yardim_talepleri, mesafe_matrisi, koordinatlar, depo_indexleri, kapasite=30):
    graph = nx.from_pandas_adjacency(mesafe_matrisi, create_using=nx.DiGraph)
    plt.figure(figsize=(8, 6)) 
    colors = ['red', 'blue', 'green', 'purple', 'orange']

    for kume_no in range(yardim_talepleri['Kume'].nunique()):
        kume_noktalar = yardim_talepleri[yardim_talepleri['Kume'] == kume_no]
        plt.scatter(kume_noktalar['X'], kume_noktalar['Y'], s=100, color=colors[kume_no], label=f"Küme {kume_no}")
        print(f"Küme {kume_no}: {kume_noktalar.index.tolist()}") 

        for i, row in kume_noktalar.iterrows():
            plt.text(row['X'], row['Y'], row.name, fontsize=8, ha='right')
        rota = []
        toplam_yuk = 0

        for nokta in kume_noktalar.index:
            if toplam_yuk + 1 <= kapasite:
                toplam_yuk += 1
                rota.append(nokta)
            else:
                tam_rota = ["Kuzey Depo"] + rota + ["Kuzey Depo"]

                for j in range(len(tam_rota) - 1):
                    a_star_rota = a_star(graph, tam_rota[j], tam_rota[j + 1])
                    if a_star_rota:
                        koordinatlar_x = [koordinatlar[mesafe_matrisi.index.get_loc(n)][0] for n in a_star_rota]
                        koordinatlar_y = [koordinatlar[mesafe_matrisi.index.get_loc(n)][1] for n in a_star_rota]
                        plt.plot(koordinatlar_x, koordinatlar_y, linestyle='--', label=f"Rota {j}")

                toplam_yuk = 0
                rota = [nokta]

    for idx, depo_kor in enumerate(koordinatlar[:depo_sayisi]):
        depo_ismi = "Kuzey Depo" if idx == 0 else "Güney Depo"
        plt.scatter(depo_kor[0], depo_kor[1], s=200, c='black', label=f'{depo_ismi}', marker='X')

    plt.title("Kümeler ve Depolar")
    plt.xlabel("X Koordinat")
    plt.ylabel("Y Koordinat")
    plt.legend()
    plt.grid(True)
    plt.show()


def her_kume_icin_ayri_grafik(yardim_talepleri, koordinatlar, depo_koordinatlari, depo_indexleri):
    colors = ['red', 'blue', 'green', 'purple', 'orange']
    
    for kume_no in range(yardim_talepleri['Kume'].nunique()):    
        plt.figure(figsize=(8, 6))  
        kume_noktalar = yardim_talepleri[yardim_talepleri['Kume'] == kume_no]
        plt.scatter(kume_noktalar['X'], kume_noktalar['Y'], s=100, color=colors[kume_no], label=f"Küme {kume_no}")

        for i, row in kume_noktalar.iterrows():
            plt.text(row['X'], row['Y'], f"{row.name}", fontsize=8, ha='right')  # İhtiyaç noktası numaraları gösteriliyor

        for idx, depo_kor in enumerate(depo_koordinatlari):
            depo_ismi = "Kuzey Depo" if idx == 0 else "Güney Depo"
            plt.scatter(depo_kor[0], depo_kor[1], s=300, c='black', label=f'{depo_ismi}', marker='X')

        plt.title(f"Küme {kume_no} - Drone Rotaları ve Noktalar")
        plt.xlabel("X Koordinat")
        plt.ylabel("Y Koordinat")
        plt.legend()
        plt.grid(True)
        output_dir = "kumeleme_cikti_grafikleri"
        plt.savefig(os.path.join(output_dir, f'kume_{kume_no}_grafik.png'))  
        print(f"{kume_no}. drone rotası kaydedildi (drone_rotalari_cikti_grafikleri içerisinde)")
        plt.close()


depo_koordinatlari = koordinatlar[:depo_sayisi]
dron_gorsel_a_star(yardim_talepleri, mesafe_matrisi, koordinatlar, depo_indexleri, kapasite=30)
her_kume_icin_ayri_grafik(yardim_talepleri, koordinatlar, depo_koordinatlari, depo_indexleri)


def her_kume_icin_drone_grafik(yardim_talepleri, koordinatlar, depo_koordinatlari, depo_indexleri, kapasite=30):
    drone_renkleri = ['red', 'blue', 'green', 'purple', 'orange', 'cyan', 'magenta', 'yellow', 'black']
    kuzey_drone_no = 1
    guney_drone_no = 1

    for kume_no in sorted(yardim_talepleri['Kume'].unique()):  # Kümeleri sıralı şekilde işle
        plt.figure(figsize=(10, 8))

        # Küme noktalarını al
        kume_noktalar = yardim_talepleri[yardim_talepleri['Kume'] == kume_no]
        if kume_noktalar.empty: 
            continue

        depo_index = 0 if kume_no in [0, 3] else 1
        depo_kor = depo_koordinatlari[depo_index]
        toplam_talep = 0
        rota = []
        renk_index = 0

        for i, row in kume_noktalar.iterrows():
            talep = row['Tıbbi Malzeme'] + row['Yiyecek']
            if toplam_talep + talep <= kapasite:
                toplam_talep += talep
                rota.append(i)
            else:
                tam_rota = [depo_index] + rota + [depo_index]
                renk = drone_renkleri[renk_index % len(drone_renkleri)]
                renk_index += 1

                drone_no = kuzey_drone_no if depo_index == 0 else guney_drone_no
                if depo_index == 0:
                    kuzey_drone_no += 1
                else:
                    guney_drone_no += 1

                for j in range(len(tam_rota) - 1):
                    x_start = depo_kor[0] if tam_rota[j] == depo_index else kume_noktalar.loc[tam_rota[j], 'X']
                    y_start = depo_kor[1] if tam_rota[j] == depo_index else kume_noktalar.loc[tam_rota[j], 'Y']
                    x_end = depo_kor[0] if tam_rota[j + 1] == depo_index else kume_noktalar.loc[tam_rota[j + 1], 'X']
                    y_end = depo_kor[1] if tam_rota[j + 1] == depo_index else kume_noktalar.loc[tam_rota[j + 1], 'Y']
                    plt.plot([x_start, x_end], [y_start, y_end], linestyle='--', color=renk, label=f"Drone {drone_no}" if j == 0 else None)

                toplam_talep = talep
                rota = [i]

        # Son rotayı çizme
        if rota:
            tam_rota = [depo_index] + rota + [depo_index]
            renk = drone_renkleri[renk_index % len(drone_renkleri)]

            drone_no = kuzey_drone_no if depo_index == 0 else guney_drone_no
            if depo_index == 0:
                kuzey_drone_no += 1
            else:
                guney_drone_no += 1

            for j in range(len(tam_rota) - 1):
                x_start = depo_kor[0] if tam_rota[j] == depo_index else kume_noktalar.loc[tam_rota[j], 'X']
                y_start = depo_kor[1] if tam_rota[j] == depo_index else kume_noktalar.loc[tam_rota[j], 'Y']
                x_end = depo_kor[0] if tam_rota[j + 1] == depo_index else kume_noktalar.loc[tam_rota[j + 1], 'X']
                y_end = depo_kor[1] if tam_rota[j + 1] == depo_index else kume_noktalar.loc[tam_rota[j + 1], 'Y']
                plt.plot([x_start, x_end], [y_start, y_end], linestyle='--', color=renk, label=f"Drone {drone_no}" if j == 0 else None)

        plt.scatter(kume_noktalar['X'], kume_noktalar['Y'], color='black', s=100, label=f"Küme {kume_no}")
        for i, row in kume_noktalar.iterrows():
            plt.text(row['X'], row['Y'], f"{row.name} ({row['Tıbbi Malzeme'] + row['Yiyecek']} birim)", fontsize=8, ha='right')
        # Sonuçları kaydetmek için çıktı dizisini belirliyoruz
        output_dir = "drone_rotalari_cikti_grafikleri"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"kume_{kume_no}_rota.png")
        print(f"kümelemenin {kume_no}. grafiği kaydedildi (kumeleme_cikti_grafikleri içerisinde.)")
        plt.scatter(depo_kor[0], depo_kor[1], color='black', marker='X', s=200, label=f"Depo {depo_index}")
        plt.title(f"Küme {kume_no} - Drone Rotaları ve İhtiyaç Talepleri")
        plt.xlabel("X Koordinat")
        plt.ylabel("Y Koordinat")
        plt.legend(loc='upper right')
        plt.grid(True)
        plt.savefig(output_file)
        plt.close()

her_kume_icin_drone_grafik(yardim_talepleri, koordinatlar, depo_koordinatlari, depo_indexleri)


def duzeltilmis_indekslerle_rotalar(yardim_talepleri, mesafe_matrisi, koordinatlar, depo_indexleri, kapasite=30):
    graph = nx.from_pandas_adjacency(mesafe_matrisi, create_using=nx.DiGraph)
    depo_names = ["Kuzey Depo", "Güyey Depo"]
    routes = []

    for kume_no in sorted(yardim_talepleri['Kume'].unique()):  
        if kume_no in [0, 3]:
            depo_index = 0  # Kuzey Deposu
        elif kume_no in [1, 2, 4]:
            depo_index = 1  # Güney Deposu
        else:
            depo_index = 0  # Varsayılan olarak Kuzey Deposu

        depo_name = depo_names[depo_index]
        toplam_yuk = 0
        rota = []

        kume_noktalar = yardim_talepleri[yardim_talepleri['Kume'] == kume_no]  # Kümeye ait noktaları filtreliyoruz

        for i, row in kume_noktalar.iterrows():
            talep = row['Tıbbi Malzeme'] + row['Yiyecek']
            if toplam_yuk + talep <= kapasite:
                toplam_yuk += talep
                rota.append((i, talep))
            else:
                routes.append((kume_no, depo_name, rota))
                toplam_yuk = talep
                rota = [(i, talep)]

        if rota:
            routes.append((kume_no, depo_name, rota))

    output = []
    clusters = []
    for kume_no, depo_name, rota in routes:
        route_str = f"{depo_name}"
        for nokta, talep in rota:
            route_str += f" -> Nokta {nokta} (ihtiyac {talep} birim)"
        route_str += f" -> {depo_name}"
        output.append(route_str)
        clusters.append(kume_no)

    return pd.DataFrame({"Cluster": clusters, "Route": output})

duzeltilmis_rotalar_df = duzeltilmis_indekslerle_rotalar(
    yardim_talepleri, mesafe_matrisi, koordinatlar, depo_indexleri, kapasite=30
)

duzeltilmis_rotalar_df.to_csv("drone_rota_ciktilari.csv", index=False)
print(duzeltilmis_rotalar_df)