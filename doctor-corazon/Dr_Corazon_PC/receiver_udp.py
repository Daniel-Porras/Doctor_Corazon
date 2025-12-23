# receiver_udp.py
#
# Recibe EASI desde ESP32 por UDP, procesa en ventanas de 10 s,
# transforma a XYZ normalizado [-1,1], grafica en tiempo real (opcional)
# y además entrega matrices (5000,3) listas para la IA.
#
# MODIFICADO: Gráficas opcionales para no bloquear servidor web

import time
import socket
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend no-GUI para evitar bloqueos
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, iirnotch, filtfilt, resample

# ==============================
#  CONFIG UDP
# ==============================
UDP_IP = "0.0.0.0"
UDP_PORT = 5005

# ==============================
#  CONFIG SEÑAL
# ==============================
FS_IN = 853.364
WINDOW_SEC = 10.0
N_IN = int(round(FS_IN * WINDOW_SEC))   # ~8534 muestras crudas

N_OUT = 5000
FS_OUT = N_OUT / WINDOW_SEC

# ==============================
#  FILTROS
# ==============================
SOS_BP = butter(
    8, [0.5, 40.0],
    btype="bandpass", fs=FS_IN,
    output="sos"
)

B_NOTCH, A_NOTCH = iirnotch(60.0, Q=60.0, fs=FS_IN)

# ==============================
#  SOCKET UDP
# ==============================
def create_socket():
    """Crea socket UDP"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    return sock

# ==============================
#  FIGURA PARA GRAFICAR XYZ (OPCIONAL)
# ==============================

# Variables globales para gráficas (solo si se activa)
_ENABLE_PLOT = False
fig = None
ax1 = ax2 = ax3 = None
line1 = line2 = line3 = None

def init_plot():
    """Inicializa las gráficas (solo para testing standalone)"""
    global fig, ax1, ax2, ax3, line1, line2, line3, _ENABLE_PLOT
    
    _ENABLE_PLOT = True
    
    plt.style.use("ggplot")
    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, sharex=True, figsize=(10, 7),
        gridspec_kw={'hspace': 0.1}
    )

    line1, = ax1.plot([], [], label="X")
    line2, = ax2.plot([], [], label="Y")
    line3, = ax3.plot([], [], label="Z")

    for ax in (ax1, ax2, ax3):
        ax.grid(True)

    ax1.set_title("Dr Corazón – XYZ normalizado")
    ax3.set_xlabel("Tiempo [s]")
    ax1.set_ylabel("X")
    ax2.set_ylabel("Y")
    ax3.set_ylabel("Z")

    plt.ion()
    fig.show()


def _autoscale(ax, y):
    """Autoescala ejes Y"""
    ymin = float(np.min(y))
    ymax = float(np.max(y))
    if ymin == ymax:
        ymin -= 1
        ymax += 1
    margin = 0.2 * (ymax - ymin)
    ax.set_ylim(ymin - margin, ymax + margin)


# ==============================
#  PIPELINE DE PROCESADO
# ==============================

def _filt_ecg(x):
    """Filtrado pasabanda + notch"""
    x_bp = sosfiltfilt(SOS_BP, x)
    x_n = filtfilt(B_NOTCH, A_NOTCH, x_bp)
    return x_n

def _normalize_centered(sig):
    """Normalización centrada a [-1, 1]"""
    sig_c = sig - np.mean(sig)
    max_abs = np.max(np.abs(sig_c))
    if max_abs < 1e-9:
        return np.zeros_like(sig_c)
    return sig_c / max_abs

def _process_packet(es_arr, as_arr, ai_arr, alab_arr):
    """
    Procesa un paquete EASI y lo convierte a XYZ normalizado
    
    Returns:
        tuple: (X_out, Y_out, Z_out) cada uno de 5000 muestras
    """
    # 1) FILTROS
    es_f = _filt_ecg(es_arr)
    as_f = _filt_ecg(as_arr)
    ai_f = _filt_ecg(ai_arr)

    # 2) REMOVER OFFSET
    es_d = es_f - np.mean(es_f)
    as_d = as_f - np.mean(as_f)
    ai_d = ai_f - np.mean(ai_f)

    # 3) TRANSFORMACIÓN EASI → XYZ
    X = 0.068 * es_d + (-0.022) * as_d + 0.794 * ai_d
    Y = 0.004 * es_d + 1.056 * as_d + (-0.900) * ai_d
    Z = -0.650 * es_d + 0.418 * as_d + (-0.421) * ai_d

    # 4) NORMALIZACIÓN [-1,1]
    Xn = _normalize_centered(X)
    Yn = _normalize_centered(Y)
    Zn = _normalize_centered(Z)

    # 5) REMUESTREO 5000 muestras
    X_out = resample(Xn, N_OUT)
    Y_out = resample(Yn, N_OUT)
    Z_out = resample(Zn, N_OUT)

    return X_out, Y_out, Z_out


# ==============================
#  GENERADOR PRINCIPAL
# ==============================

def receive_packets(enable_plot=False):
    """
    Generador que:
      - Recibe UDP continuo de ES AS AI ALAB
      - Procesa ventanas de ~10 s
      - Grafica X, Y, Z (solo si enable_plot=True)
      - YIELDea matriz (5000 x 3) lista para IA
    
    Args:
        enable_plot (bool): Si True, muestra gráficas matplotlib
    
    Yields:
        np.ndarray: Array de shape (5000, 3) con [X, Y, Z]
    """
    global _ENABLE_PLOT
    
    # Inicializar gráficas si se solicita
    if enable_plot:
        init_plot()
    
    # Crear socket
    sock = create_socket()
    print(f"[receiver_udp] Escuchando UDP en {UDP_IP}:{UDP_PORT} ...")
    
    # Buffers para datos crudos
    raw_es = []
    raw_as = []
    raw_ai = []
    raw_alab = []

    print(f"[receiver_udp] Esperando paquete de {N_IN} muestras...")

    while True:
        # Leer UDP
        try:
            data, addr = sock.recvfrom(4096)
        except BlockingIOError:
            if enable_plot:
                plt.pause(0.001)
            else:
                time.sleep(0.001)
            continue

        text = data.decode("utf-8", errors="ignore")
        lines = text.splitlines()

        for line in lines:
            parts = line.strip().split()
            if len(parts) != 4:
                continue
            try:
                es_raw = int(parts[0])
                as_raw = int(parts[1])
                ai_raw = int(parts[2])
                alab   = int(parts[3])
            except:
                continue

            raw_es.append(es_raw)
            raw_as.append(as_raw)
            raw_ai.append(ai_raw)
            raw_alab.append(alab)

            # ¿Paquete completo?
            if len(raw_es) >= N_IN:

                es_arr = np.asarray(raw_es[:N_IN], float)
                as_arr = np.asarray(raw_as[:N_IN], float)
                ai_arr = np.asarray(raw_ai[:N_IN], float)
                alab_arr = np.asarray(raw_alab[:N_IN], int)

                print(f"[receiver_udp] Paquete listo: {N_IN} muestras. Procesando...")

                # PROCESAR
                X_out, Y_out, Z_out = _process_packet(es_arr, as_arr, ai_arr, alab_arr)

                # --- GRAFICAR (solo si está habilitado) ---
                if enable_plot and fig is not None:
                    t = np.linspace(0, WINDOW_SEC, N_OUT, endpoint=False)

                    line1.set_data(t, X_out)
                    line2.set_data(t, Y_out)
                    line3.set_data(t, Z_out)

                    ax1.set_xlim(0, WINDOW_SEC)
                    ax2.set_xlim(0, WINDOW_SEC)
                    ax3.set_xlim(0, WINDOW_SEC)

                    _autoscale(ax1, X_out)
                    _autoscale(ax2, Y_out)
                    _autoscale(ax3, Z_out)

                    fig.canvas.draw()
                    fig.canvas.flush_events()

                # --- PAQUETE PARA IA ---
                xyz = np.column_stack([X_out, Y_out, Z_out]).astype(np.float32)

                # limpiar buffers
                raw_es.clear()
                raw_as.clear()
                raw_ai.clear()
                raw_alab.clear()

                # ENTREGAR PAQUETE 5000×3
                yield xyz


# ==============================
#  PRUEBA STANDALONE
# ==============================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 TESTING: receiver_udp.py")
    print("="*60)
    print(f"\n📡 Configuración:")
    print(f"   UDP: {UDP_IP}:{UDP_PORT}")
    print(f"   Frecuencia entrada: {FS_IN} Hz")
    print(f"   Muestras por ventana: {N_IN}")
    print(f"   Salida: {N_OUT} muestras @ {FS_OUT} Hz")
    print(f"\n🎨 Gráficas: ACTIVADAS")
    print(f"   Presiona Ctrl+C para detener\n")
    print("="*60 + "\n")
    
    try:
        # En modo standalone, habilitar gráficas
        for pkt in receive_packets(enable_plot=True):
            print(f"[TEST] Paquete recibido: {pkt.shape}")
            print(f"       X: min={pkt[:, 0].min():.3f}, max={pkt[:, 0].max():.3f}")
            print(f"       Y: min={pkt[:, 1].min():.3f}, max={pkt[:, 1].max():.3f}")
            print(f"       Z: min={pkt[:, 2].min():.3f}, max={pkt[:, 2].max():.3f}")
            print()
    except KeyboardInterrupt:
        print("\n[receiver_udp] Cerrando.")
