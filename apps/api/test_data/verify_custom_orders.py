import httpx
import json
import time
import pandas as pd
import io

API_URL = "http://localhost:8000"

tsv_data = """order_id	order_date	sku	city	payment_mode	revenue	customer_type
KFT00002	2026-05-05	Nomad Classic	Delhi	COD	2727	new
KFT00003	2026-05-14	Nomad Classic	Delhi	Prepaid	2588	repeat
KFT00004	2026-05-01	Strider Pro	Mumbai	COD	2207	new
KFT00005	2026-05-08	Flex Run	Hyderabad	Prepaid	2013	new
KFT00006	2026-05-06	Urban Step	Pune	Prepaid	2011	new
KFT00007	2026-05-04	Nomad Classic	Surat	COD	2843	new
KFT00008	2026-05-09	Strider Pro	Surat	COD	2208	repeat
KFT00009	2026-05-03	Strider Pro	Lucknow	Prepaid	2092	repeat
KFT00010	2026-05-12	Flex Run	Pune	Prepaid	2240	new
KFT00011	2026-05-10	Flex Run	Hyderabad	Prepaid	1915	new
KFT00012	2026-05-12	Strider Pro	Hyderabad	Prepaid	2131	new
KFT00013	2026-05-03	Canvas Elite	Jaipur	COD	1658	new
KFT00014	2026-05-13	Flex Run	Bangalore	COD	2035	new
KFT00015	2026-05-08	Trail Blaze	Hyderabad	Prepaid	2256	repeat
KFT00016	2026-05-11	Strider Pro	Jaipur	COD	2366	new
KFT00017	2026-05-05	Canvas Elite	Lucknow	COD	1533	repeat
KFT00018	2026-05-14	Trail Blaze	Bangalore	COD	2468	new
KFT00019	2026-05-17	Flex Run	Surat	COD	1869	repeat
KFT00020	2026-05-06	Urban Step	Delhi	Prepaid	1677	repeat
KFT00021	2026-05-15	Nomad Classic	Surat	Prepaid	3109	new
KFT00022	2026-05-04	Flex Run	Pune	Prepaid	1804	repeat
KFT00023	2026-05-14	Nomad Classic	Pune	Prepaid	2799	new
KFT00024	2026-05-09	Canvas Elite	Lucknow	COD	1667	repeat
KFT00025	2026-05-10	Flex Run	Bangalore	COD	2119	new
KFT00026	2026-05-17	Nomad Classic	Hyderabad	COD	3051	repeat
KFT00027	2026-05-10	Strider Pro	Jaipur	Prepaid	2084	new
KFT00028	2026-05-03	Canvas Elite	Mumbai	COD	1339	new
KFT00029	2026-05-05	Nomad Classic	Lucknow	Prepaid	3044	repeat
KFT00030	2026-05-14	Canvas Elite	Lucknow	Prepaid	1569	new
KFT00031	2026-05-12	Canvas Elite	Hyderabad	Prepaid	1642	new
KFT00032	2026-05-01	Urban Step	Lucknow	COD	1772	new
KFT00033	2026-05-02	Flex Run	Hyderabad	COD	2161	new
KFT00034	2026-05-17	Canvas Elite	Delhi	Prepaid	1335	repeat
KFT00035	2026-05-16	Canvas Elite	Pune	COD	1366	new
KFT00036	2026-05-14	Canvas Elite	Lucknow	Prepaid	1348	new
KFT00037	2026-05-04	Trail Blaze	Surat	COD	2254	repeat
KFT00038	2026-05-08	Strider Pro	Surat	Prepaid	1954	repeat
KFT00039	2026-05-09	Canvas Elite	Hyderabad	COD	1392	new
KFT00040	2026-05-04	Urban Step	Hyderabad	Prepaid	2012	new
KFT00041	2026-05-08	Strider Pro	Mumbai	Prepaid	2333	repeat
KFT00042	2026-05-02	Canvas Elite	Surat	COD	1504	new
KFT00043	2026-05-15	Canvas Elite	Surat	COD	1773	new
KFT00044	2026-05-16	Trail Blaze	Surat	Prepaid	2768	repeat
KFT00045	2026-05-02	Canvas Elite	Hyderabad	COD	1595	repeat
KFT00046	2026-05-17	Nomad Classic	Jaipur	COD	3013	new
KFT00047	2026-05-03	Canvas Elite	Mumbai	Prepaid	1394	new
KFT00048	2026-05-08	Flex Run	Delhi	COD	1860	new
KFT00049	2026-05-17	Flex Run	Mumbai	COD	2097	new
KFT00050	2026-05-09	Trail Blaze	Pune	COD	2443	new
KFT00051	2026-05-03	Urban Step	Bangalore	COD	1760	new
KFT00052	2026-05-03	Strider Pro	Lucknow	Prepaid	1950	new
KFT00053	2026-05-03	Flex Run	Hyderabad	COD	1977	new
KFT00054	2026-05-10	Canvas Elite	Jaipur	COD	1577	new
KFT00055	2026-05-04	Flex Run	Mumbai	COD	2276	new
KFT00056	2026-05-05	Canvas Elite	Pune	COD	1582	new
KFT00057	2026-05-09	Trail Blaze	Pune	Prepaid	2407	new
KFT00058	2026-05-03	Flex Run	Lucknow	COD	1825	repeat
KFT00059	2026-05-05	Nomad Classic	Surat	Prepaid	2840	new
KFT00060	2026-05-01	Nomad Classic	Pune	COD	2936	new
KFT00061	2026-05-02	Strider Pro	Delhi	Prepaid	1975	new
KFT00062	2026-05-02	Trail Blaze	Bangalore	COD	2572	new
KFT00063	2026-05-14	Trail Blaze	Hyderabad	Prepaid	2561	new
KFT00064	2026-05-06	Flex Run	Bangalore	Prepaid	1882	new
KFT00065	2026-05-14	Urban Step	Mumbai	COD	1999	repeat
KFT00066	2026-05-13	Nomad Classic	Hyderabad	COD	2609	repeat
KFT00067	2026-05-12	Strider Pro	Lucknow	COD	2134	repeat
KFT00068	2026-05-11	Trail Blaze	Hyderabad	COD	2607	new
KFT00069	2026-05-13	Trail Blaze	Delhi	Prepaid	2720	new
KFT00070	2026-05-06	Nomad Classic	Jaipur	Prepaid	2766	new
KFT00071	2026-05-11	Flex Run	Pune	COD	1975	new
KFT00072	2026-05-02	Urban Step	Delhi	COD	1729	new
KFT00073	2026-05-07	Nomad Classic	Surat	COD	3050	repeat
KFT00074	2026-05-11	Trail Blaze	Surat	COD	2537	new
KFT00075	2026-05-14	Nomad Classic	Delhi	Prepaid	2815	new
KFT00076	2026-05-14	Trail Blaze	Surat	Prepaid	2395	new
KFT00077	2026-05-10	Nomad Classic	Surat	Prepaid	3129	repeat
KFT00078	2026-05-11	Urban Step	Mumbai	COD	2001	new
KFT00079	2026-05-06	Urban Step	Lucknow	COD	1841	new
KFT00080	2026-05-11	Nomad Classic	Delhi	COD	3133	new
KFT00081	2026-05-05	Strider Pro	Hyderabad	Prepaid	2000	new
KFT00082	2026-05-03	Strider Pro	Mumbai	COD	2334	new
KFT00083	2026-05-13	Urban Step	Surat	Prepaid	1966	new
KFT00084	2026-05-04	Urban Step	Surat	COD	1601	new
KFT00085	2026-05-15	Urban Step	Hyderabad	COD	1864	repeat
KFT00086	2026-05-15	Strider Pro	Hyderabad	Prepaid	1967	new
KFT00087	2026-05-17	Nomad Classic	Jaipur	Prepaid	3126	repeat
KFT00088	2026-05-15	Urban Step	Lucknow	Prepaid	1842	repeat
KFT00089	2026-05-16	Trail Blaze	Hyderabad	Prepaid	2732	new
KFT00090	2026-05-08	Nomad Classic	Hyderabad	COD	2791	new
KFT00091	2026-05-05	Trail Blaze	Jaipur	COD	2340	new
KFT00092	2026-05-14	Canvas Elite	Surat	Prepaid	1331	new
KFT00093	2026-05-14	Urban Step	Jaipur	COD	1704	new
KFT00094	2026-05-16	Urban Step	Mumbai	Prepaid	1793	repeat
KFT00095	2026-05-14	Strider Pro	Jaipur	COD	2355	new
KFT00096	2026-05-01	Flex Run	Hyderabad	COD	2047	new
KFT00097	2026-05-06	Urban Step	Jaipur	COD	1969	repeat
KFT00098	2026-05-13	Urban Step	Bangalore	Prepaid	2063	new
KFT00099	2026-05-15	Flex Run	Mumbai	COD	2242	new
KFT00100	2026-05-11	Canvas Elite	Mumbai	COD	1531	new
KFT00101	2026-05-09	Trail Blaze	Surat	COD	2630	repeat
KFT00102	2026-05-12	Strider Pro	Lucknow	COD	2386	new
KFT00103	2026-05-01	Canvas Elite	Delhi	Prepaid	1685	new
KFT00104	2026-05-05	Canvas Elite	Hyderabad	Prepaid	1421	new
KFT00105	2026-05-09	Urban Step	Delhi	COD	1957	new
KFT00106	2026-05-06	Trail Blaze	Bangalore	Prepaid	2316	repeat
KFT00107	2026-05-13	Trail Blaze	Delhi	Prepaid	2788	repeat
KFT00108	2026-05-08	Urban Step	Hyderabad	COD	1920	new
KFT00109	2026-05-02	Strider Pro	Pune	Prepaid	1960	new
KFT00110	2026-05-01	Trail Blaze	Surat	Prepaid	2548	new
KFT00111	2026-05-15	Urban Step	Lucknow	COD	1924	repeat
KFT00112	2026-05-09	Nomad Classic	Bangalore	COD	3165	repeat
KFT00113	2026-05-09	Flex Run	Lucknow	COD	2102	repeat
KFT00114	2026-05-08	Trail Blaze	Hyderabad	Prepaid	2660	new
KFT00115	2026-05-06	Urban Step	Surat	COD	1765	new
KFT00116	2026-05-09	Urban Step	Hyderabad	COD	1742	new
KFT00117	2026-05-14	Flex Run	Mumbai	COD	1922	new
KFT00118	2026-05-15	Urban Step	Hyderabad	Prepaid	1850	new
KFT00119	2026-05-10	Strider Pro	Delhi	COD	2023	new
KFT00120	2026-05-11	Nomad Classic	Jaipur	Prepaid	2934	new
KFT00121	2026-05-07	Trail Blaze	Lucknow	COD	2322	new
KFT00122	2026-05-07	Trail Blaze	Delhi	Prepaid	2388	repeat
KFT00123	2026-05-17	Canvas Elite	Lucknow	COD	1688	new
KFT00124	2026-05-08	Flex Run	Pune	Prepaid	1950	repeat
KFT00125	2026-05-09	Trail Blaze	Bangalore	COD	2328	new
KFT00126	2026-05-16	Strider Pro	Mumbai	Prepaid	1963	new
KFT00127	2026-05-11	Strider Pro	Mumbai	Prepaid	2124	new
KFT00128	2026-05-03	Canvas Elite	Mumbai	COD	1357	repeat
KFT00129	2026-05-05	Urban Step	Lucknow	COD	1626	new
KFT00130	2026-05-14	Canvas Elite	Pune	COD	1584	new
KFT00131	2026-05-15	Flex Run	Hyderabad	Prepaid	2264	new
KFT00132	2026-05-07	Trail Blaze	Surat	COD	2300	new
KFT00133	2026-05-06	Nomad Classic	Hyderabad	COD	2744	new
KFT00134	2026-05-16	Flex Run	Delhi	COD	2151	new
KFT00135	2026-05-03	Trail Blaze	Mumbai	COD	2663	new
KFT00136	2026-05-07	Nomad Classic	Hyderabad	Prepaid	3139	repeat
KFT00137	2026-05-09	Urban Step	Delhi	COD	2064	new
KFT00138	2026-05-10	Canvas Elite	Delhi	COD	1603	repeat
KFT00139	2026-05-09	Urban Step	Delhi	COD	1805	new
KFT00140	2026-05-14	Flex Run	Lucknow	COD	2254	new
KFT00141	2026-05-01	Nomad Classic	Jaipur	Prepaid	2733	new
KFT00142	2026-05-16	Nomad Classic	Pune	Prepaid	2678	repeat
KFT00143	2026-05-14	Flex Run	Lucknow	Prepaid	2098	new
KFT00144	2026-05-11	Nomad Classic	Lucknow	Prepaid	2917	new
KFT00145	2026-05-10	Trail Blaze	Delhi	Prepaid	2706	new
KFT00146	2026-05-03	Nomad Classic	Surat	Prepaid	2964	new
KFT00147	2026-05-17	Trail Blaze	Pune	COD	2612	repeat
KFT00148	2026-05-16	Strider Pro	Lucknow	COD	2084	new
KFT00149	2026-05-05	Nomad Classic	Lucknow	Prepaid	3061	new
KFT00150	2026-05-08	Trail Blaze	Lucknow	Prepaid	2228	new
KFT00151	2026-05-03	Nomad Classic	Bangalore	COD	2916	new
KFT00152	2026-05-05	Canvas Elite	Delhi	COD	1725	new
KFT00153	2026-05-16	Urban Step	Pune	COD	2026	new
KFT00154	2026-05-17	Urban Step	Hyderabad	COD	1696	new
KFT00155	2026-05-11	Nomad Classic	Bangalore	Prepaid	2923	new
KFT00156	2026-05-16	Flex Run	Pune	Prepaid	1951	new
KFT00157	2026-05-13	Canvas Elite	Lucknow	COD	1581	new
KFT00158	2026-05-13	Urban Step	Jaipur	Prepaid	1721	repeat
KFT00159	2026-05-13	Canvas Elite	Surat	COD	1660	repeat
KFT00160	2026-05-11	Urban Step	Bangalore	COD	1856	new
KFT00161	2026-05-05	Strider Pro	Lucknow	COD	1906	repeat
KFT00162	2026-05-11	Urban Step	Bangalore	COD	1734	repeat
KFT00163	2026-05-13	Flex Run	Surat	COD	2235	repeat
KFT00164	2026-05-08	Trail Blaze	Lucknow	Prepaid	2269	new
KFT00165	2026-05-04	Nomad Classic	Pune	Prepaid	2943	repeat
KFT00166	2026-05-02	Nomad Classic	Delhi	COD	2528	new
KFT00167	2026-05-08	Trail Blaze	Mumbai	COD	2348	new
KFT00168	2026-05-06	Flex Run	Surat	COD	1886	repeat
KFT00169	2026-05-05	Strider Pro	Surat	Prepaid	2366	new
KFT00170	2026-05-01	Canvas Elite	Lucknow	COD	1640	new
KFT00171	2026-05-12	Urban Step	Pune	COD	1825	new
KFT00172	2026-05-15	Flex Run	Pune	COD	1927	new
KFT00173	2026-05-08	Trail Blaze	Hyderabad	Prepaid	2308	repeat
KFT00174	2026-05-01	Urban Step	Jaipur	COD	1750	repeat
KFT00175	2026-05-16	Nomad Classic	Surat	COD	2549	new
KFT00176	2026-05-09	Trail Blaze	Hyderabad	Prepaid	2393	new
KFT00177	2026-05-02	Nomad Classic	Bangalore	Prepaid	3160	repeat
KFT00178	2026-05-03	Trail Blaze	Lucknow	COD	2333	new
KFT00179	2026-05-12	Trail Blaze	Jaipur	Prepaid	2334	new
KFT00180	2026-05-16	Flex Run	Pune	Prepaid	2221	new
KFT00181	2026-05-05	Trail Blaze	Jaipur	Prepaid	2276	new
KFT00182	2026-05-03	Canvas Elite	Surat	Prepaid	1486	repeat
KFT00183	2026-05-09	Urban Step	Mumbai	COD	1787	new
KFT00184	2026-05-08	Flex Run	Surat	Prepaid	1854	repeat
KFT00185	2026-05-08	Urban Step	Mumbai	COD	1766	repeat
KFT00186	2026-05-14	Nomad Classic	Delhi	Prepaid	2808	new
KFT00187	2026-05-04	Strider Pro	Bangalore	COD	2151	new
KFT00188	2026-05-12	Strider Pro	Hyderabad	Prepaid	2131	new
KFT00189	2026-05-04	Nomad Classic	Surat	Prepaid	2923	repeat
KFT00190	2026-05-12	Urban Step	Surat	Prepaid	1952	new
KFT00191	2026-05-04	Canvas Elite	Lucknow	COD	1484	new
KFT00192	2026-05-02	Nomad Classic	Jaipur	Prepaid	2866	repeat
KFT00193	2026-05-15	Urban Step	Pune	COD	2033	new
KFT00194	2026-05-02	Strider Pro	Hyderabad	Prepaid	1909	new
KFT00195	2026-05-03	Trail Blaze	Hyderabad	Prepaid	2409	repeat
KFT00196	2026-05-11	Flex Run	Hyderabad	COD	1918	repeat
KFT00197	2026-05-09	Canvas Elite	Mumbai	COD	1365	repeat
KFT00198	2026-05-12	Canvas Elite	Delhi	COD	1306	new
KFT00199	2026-05-14	Canvas Elite	Jaipur	COD	1363	new
KFT00200	2026-05-12	Flex Run	Delhi	Prepaid	2197	new
KFT00201	2026-05-02	Flex Run	Delhi	COD	2113	new
KFT00202	2026-05-16	Nomad Classic	Pune	Prepaid	2561	repeat
KFT00203	2026-05-15	Urban Step	Surat	Prepaid	2064	new
KFT00204	2026-05-09	Strider Pro	Delhi	COD	1963	new
KFT00205	2026-05-15	Flex Run	Jaipur	COD	1949	new
KFT00206	2026-05-07	Flex Run	Surat	COD	2235	new
KFT00207	2026-05-15	Urban Step	Lucknow	Prepaid	2022	new
KFT00208	2026-05-09	Urban Step	Surat	Prepaid	1759	new
KFT00209	2026-05-03	Trail Blaze	Bangalore	Prepaid	2292	new
KFT00210	2026-05-05	Strider Pro	Surat	COD	2314	repeat
KFT00211	2026-05-04	Flex Run	Mumbai	COD	1967	new
KFT00212	2026-05-02	Urban Step	Jaipur	Prepaid	1815	repeat
KFT00213	2026-05-05	Trail Blaze	Pune	COD	2416	new
KFT00214	2026-05-12	Nomad Classic	Lucknow	COD	3068	new
KFT00215	2026-05-01	Strider Pro	Pune	Prepaid	2331	repeat
KFT00216	2026-05-10	Flex Run	Pune	COD	2189	new
KFT00217	2026-05-13	Trail Blaze	Jaipur	COD	2778	repeat
KFT00218	2026-05-17	Strider Pro	Bangalore	Prepaid	1945	repeat
KFT00219	2026-05-10	Canvas Elite	Surat	COD	1488	new
KFT00220	2026-05-02	Nomad Classic	Jaipur	Prepaid	2585	new
KFT00221	2026-05-09	Canvas Elite	Bangalore	Prepaid	1340	new
KFT00222	2026-05-07	Urban Step	Surat	COD	1738	new
KFT00223	2026-05-16	Flex Run	Delhi	COD	2146	new
KFT00224	2026-05-02	Flex Run	Pune	COD	2105	new
KFT00225	2026-05-09	Strider Pro	Hyderabad	COD	1969	new
KFT00226	2026-05-06	Trail Blaze	Jaipur	COD	2639	new
KFT00227	2026-05-12	Canvas Elite	Surat	COD	1585	new
KFT00228	2026-05-15	Strider Pro	Surat	Prepaid	1908	new
KFT00229	2026-05-14	Strider Pro	Jaipur	Prepaid	2262	new
KFT00230	2026-05-15	Trail Blaze	Delhi	COD	2374	repeat
KFT00231	2026-05-14	Nomad Classic	Jaipur	COD	2748	repeat
KFT00232	2026-05-11	Flex Run	Surat	COD	1957	new
KFT00233	2026-05-04	Canvas Elite	Jaipur	Prepaid	1623	new
KFT00234	2026-05-05	Flex Run	Hyderabad	Prepaid	2171	new
KFT00235	2026-05-05	Canvas Elite	Delhi	COD	1607	new
KFT00236	2026-05-15	Nomad Classic	Delhi	COD	3004	repeat
KFT00237	2026-05-11	Flex Run	Lucknow	Prepaid	2128	repeat
KFT00238	2026-05-10	Nomad Classic	Jaipur	COD	2951	new
KFT00239	2026-05-15	Trail Blaze	Mumbai	COD	2671	new
KFT00240	2026-05-03	Strider Pro	Mumbai	COD	2229	new
KFT00241	2026-05-02	Flex Run	Surat	COD	2204	new
KFT00242	2026-05-02	Urban Step	Hyderabad	COD	1676	new
KFT00243	2026-05-03	Urban Step	Delhi	Prepaid	1964	repeat
KFT00244	2026-05-17	Flex Run	Bangalore	COD	2023	new
KFT00245	2026-05-14	Flex Run	Bangalore	COD	1997	repeat
KFT00246	2026-05-11	Trail Blaze	Mumbai	Prepaid	2266	new
KFT00247	2026-05-05	Strider Pro	Surat	COD	2235	repeat
KFT00248	2026-05-10	Trail Blaze	Delhi	Prepaid	2557	new
KFT00249	2026-05-10	Nomad Classic	Surat	COD	2585	new
KFT00250	2026-05-17	Flex Run	Surat	COD	1864	new
KFT00251	2026-05-06	Strider Pro	Surat	Prepaid	2057	new"""

def test_pipeline_with_custom_orders():
    # 0. Convert TSV text to actual pandas Excel sheet
    df = pd.read_csv(io.StringIO(tsv_data), sep="\t")
    file_path = "test_data/custom_operator_data.xlsx"
    df.to_excel(file_path, index=False)
    print(f"Generated test file at {file_path} with shapes: {df.shape}")

    print("\n1. Resetting database to start completely fresh...")
    res_reset = httpx.post(f"{API_URL}/reset")
    print(f"Database Reset Response: {res_reset.json()}")

    print("\n2. Sending preview request for custom shopify orders...")
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = httpx.post(
            f"{API_URL}/uploads/preview",
            params={"brand_id": "brand_unigo", "upload_source": "shopify_orders"},
            files=files
        )
        
    if response.status_code != 200:
        print(f"Error previewing file: {response.text}")
        return
        
    preview_data = response.json()
    print("Preview successful!")
    print(f"Uploaded columns: {preview_data['columns']}")
    print(f"Suggested mappings: {preview_data['suggestions']}")
    
    # 3. Build mappings (exact matches)
    mapping = {
        "campaign_id": "order_id",
        "sku_id": "sku",
        "cod_orders": "payment_mode",
        "revenue": "revenue"
    }
            
    print(f"\n4. Confirming mapping and launching Celery task: {mapping}")
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {
            "brand_id": "brand_unigo",
            "upload_source": "shopify_orders",
            "mapping": json.dumps(mapping)
        }
        response = httpx.post(
            f"{API_URL}/uploads/confirm",
            data=data,
            files=files
        )
        
    if response.status_code != 200:
        print(f"Error confirming mapping: {response.text}")
        return
        
    confirm_data = response.json()
    task_id = confirm_data["task_id"]
    print(f"Celery task launched successfully! Task ID: {task_id}")
    
    print("\n5. Polling Celery task status until complete...")
    status = "pending"
    for _ in range(30):
        time.sleep(1)
        response = httpx.get(f"{API_URL}/uploads/status/{task_id}")
        status_data = response.json()
        status = status_data["status"]
        print(f"Current task status: {status}")
        if status in ["success", "failure"]:
            break
            
    if status == "success":
        print("\n🎉 CELERY TASK COMPLETED SUCCESSFULLY!")
        
        # Verify state is updated in DB
        print("\n6. Verifying state loaded from database...")
        state_response = httpx.get(f"{API_URL}/state?brand_id=brand_unigo")
        state_data = state_response.json()
        
        print(f"--- BRAND METADATA ---")
        print(f"Brand Name: {state_data['brandName']}")
        print(f"Latest Active Snapshot Version: v{state_data['snapshots'][0]['snapshotVersion']}")
        print(f"Is Baseline: {state_data['snapshots'][0]['isBaseline']}")
        print(f"Number of SKUs detected: {len(state_data['skus'])}")
        print(f"Unique SKUs: {[s['name'] for s in state_data['skus']]}")
        
        print(f"\n--- GENERATED DECISIONS ({len(state_data['decisions'])}) ---")
        for d in state_data['decisions']:
            print(f" - [{d['severity'].upper()}] {d['title']}")
            print(f"   Affected SKUs: {d['affectedSkus']}")
            print(f"   Affected Campaigns: {d['affectedCampaigns'][:3]}...")
            print(f"   Explanation: {d['explanation']}")
            print(f"   Impact: {d['impactLabel']}")
            print("-" * 60)
            
        # Assertions
        assert "My E-commerce Brand" in state_data['brandName'] or "My E-commerce Brand" == state_data['brandName']
        assert len(state_data['skus']) > 0
        assert any("Nomad Classic" in s["name"] for s in state_data['skus'])
        
        # Verify Unigo is gone
        assert not any("Velar Runner" in s["name"] for s in state_data['skus'])
        assert not any("Velar Runner" in d["title"] for d in state_data['decisions'])
        
        print("\n🏆 ALL DYNAMIC BRAND VERIFICATIONS PASSED!")
    else:
        print(f"\n❌ Pipeline failed or timed out: {status_data}")

if __name__ == "__main__":
    test_pipeline_with_custom_orders()
