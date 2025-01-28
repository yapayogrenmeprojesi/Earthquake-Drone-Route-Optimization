# Deprem Drone Rota Optimizasyonu Projesi

Bu projede, yardım noktalarından gelen talepler kümelenerek dronlar ile taşımacılık yapılması hedeflenmiştir. Amaç, Kuzey ve Güney olmak üzere kullanılan 2 depodan dronların kapasitesini göz önünde bulundurarak minimum mesafe ve maksimum verimlilikle yardım malzemelerini ihtiyaç noktalarına ulaştırmaktır.

## Proje İçeriği

Projemizi gerçekleştirebilmek için **ihtiyac_noktalari** ve **yardim_talepleri** adında iki Excel dosyası kullandık.

- **ihtiyac_noktalari**: İhtiyaç noktaları ve depolar arasındaki uzaklıkların kayıtlı olduğu Excel dosyamız.
- **yardim_talepleri**: Her ihtiyaç noktasının ihtiyaç duyduğu tıbbi malzeme ve yiyecek miktarlarının yazılı olduğu Excel dosyamız.

## Kümeleme (Clustering)

### K-Means Kümeleme Algoritması

İlk adımda kümeler için bir merkez noktası rastgele olarak belirlenir. Merkez eleman dışındaki elemanlar en yakın merkez noktasına göre kümelenir. Bu işlem, her bir elemanın merkez noktalara olan uzaklıkları ölçülerek yapılır. Ardından, merkez noktası stabil hale gelene kadar tekrar bir merkez noktası hesaplaması yapılır.

**WCSS (Within-Cluster Sums of Squares)** formülü, her bir küme için o kümedeki noktaların merkez noktalarına olan uzaklıklarının karelerinin toplamını ifade eder.

Biz, daha optimal sonuçlar elde etmek için **K-Mean = 5** küme sayısını seçtik. Bu sayede yardım noktalarının yakınlıklarına göre 5 kümeye ayrılmasını sağladık.

### Kümeleme Sonuçları

Kümeleme sonuçları ve seçilen küme sayısına göre kümelenmiş ihtiyaç noktalarının grafiklerini, **matplotlib** kütüphanesi ile oluşturduk. Aşağıda **Elbow Method** ve **WCSS** değerleri yer almaktadır.

## Drone Özellikleri ve Şartlar

- Her drone, kendi deposuna özgü olacak ve maksimum 30 kapasiteye kadar ürün taşıyabilir.
- Her bir drone birden fazla ihtiyaç noktasını ziyaret edebilir fakat hiçbir ihtiyaç noktasını birden fazla drone ziyaret edemez.
- İhtiyaç noktalarının ihtiyaçları, taksit taksit, taksim edilmez.

## Rota Oluşturma ve Optimize Etme

Dronların en verimli şekilde yardım malzemelerini taşımalarını sağlamak için rota optimizasyonu **A\* algoritması** ile gerçekleştirilmiştir. A\* algoritması, iki nokta arasındaki en kısa yolu bulmak için kullanılan en etkili yol bulma algoritmalarından biridir.

**A\* algoritması**, başlangıç noktasından hedef noktaya ulaşana kadar, her adımda en düşük maliyetli (en kısa mesafeli) rotayı hesaplayarak ilerler.

### A\* Algoritması Adımları

Başlangıç noktasından hedef noktaya ulaşana kadar her adımda en düşük maliyetli yolu hesaplar ve hedefe ulaşıldığında seçilen rotayı takip ederek toplam maliyeti minimize eder.

## Sonuçlar ve Çıktılar

Sonuçlarımızın çıktıları hem grafik üzerinde hem de **.csv** dosyası olarak kayıt altına alınmıştır. Aşağıda, kümeler ve rotalar için örnek bir çıktı listesi yer almaktadır.


## Kaynakça

- [Makine Öğrenmesi - Clustering Kümeleme Teknikleri](https://samed-harman.medium.com/makine-%C3%B6%C4%9Frenmesi-clustering-k%C3%BCmeleme-teknikleri-bd1b59a0a177)
- [Understanding Path Algorithms and Implementation with Python](https://towardsdatascience.com/understanding-a-path-algorithms-and-implementation-with-python-4d8458d6ccc7)
- [A* Search Algorithm - GeeksforGeeks](https://www.geeksforgeeks.org/a-search-algorithm/)
- [Elbow Method for Optimal Value of K in KMeans](https://www.geeksforgeeks.org/elbow-method-for-optimal-value-of-k-in-kmeans/)
