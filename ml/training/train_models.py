"""SentinelTrust ML Training Pipeline"""
import numpy as np, os

DEVICE_TYPES = ["ip_camera","temp_sensor","router","smart_hub","plc","smart_lock"]
FEATURE_NAMES = ["packet_rate","byte_entropy","protocol_tcp_ratio","protocol_udp_ratio",
    "dns_query_freq","unique_dest_ips","avg_connection_duration","inter_arrival_variance",
    "port_entropy","bandwidth_mbps","new_external_connections","tcp_flag_anomaly"]

PROFILES = {
    "ip_camera":  [120,5.2,0.7,0.3,5,3,2.5,0.3,1.2,2.5,0,0.05],
    "temp_sensor":[10,4.1,0.9,0.1,1,1,1.0,0.1,0.5,0.1,0,0.02],
    "router":     [500,5.8,0.6,0.4,100,30,0.5,0.8,2.5,50,2,0.08],
    "smart_hub":  [80,5.0,0.8,0.2,20,8,1.5,0.4,1.8,1.0,0,0.04],
    "plc":        [40,4.5,0.95,0.05,2,2,3.0,0.2,0.8,0.5,0,0.03],
    "smart_lock": [5,3.8,0.99,0.01,1,1,0.5,0.1,0.3,0.05,0,0.01],
}

def train():
    try:
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
        import joblib
        os.makedirs("../models", exist_ok=True)
        for dtype in DEVICE_TYPES:
            mean = np.array(PROFILES.get(dtype, PROFILES["smart_hub"]))
            std = mean * 0.15 + 0.01
            X = np.abs(np.random.normal(mean, std, (5000, len(FEATURE_NAMES))))
            scaler = StandardScaler()
            X_s = scaler.fit_transform(X)
            model = IsolationForest(n_estimators=200, contamination=0.03, random_state=42)
            model.fit(X_s)
            joblib.dump(model, f"../models/if_{dtype}.pkl")
            joblib.dump(scaler, f"../models/scaler_{dtype}.pkl")
            print(f"Trained IF for {dtype}")
    except ImportError:
        print("Install scikit-learn: pip install scikit-learn joblib")

if __name__ == "__main__":
    train()
