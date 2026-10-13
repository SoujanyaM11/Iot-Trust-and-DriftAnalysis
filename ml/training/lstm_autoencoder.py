"""LSTM Autoencoder for Temporal Drift Detection. Requires tensorflow."""

def build_lstm_autoencoder(seq_len=48, n_features=12):
    try:
        import tensorflow as tf
        from tensorflow.keras import layers, Model
        inp = tf.keras.Input(shape=(seq_len, n_features))
        x = layers.LSTM(64, return_sequences=True)(inp)
        enc = layers.LSTM(32)(x)
        x = layers.RepeatVector(seq_len)(enc)
        x = layers.LSTM(32, return_sequences=True)(x)
        x = layers.LSTM(64, return_sequences=True)(x)
        out = layers.TimeDistributed(layers.Dense(n_features))(x)
        model = Model(inp, out, name="lstm_autoencoder")
        model.compile(optimizer="adam", loss="mse")
        return model
    except ImportError:
        print("pip install tensorflow")

if __name__ == "__main__":
    m = build_lstm_autoencoder()
    if m: m.summary()
