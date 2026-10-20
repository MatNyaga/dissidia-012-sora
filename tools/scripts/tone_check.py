"""Count windows with a strong 1 kHz tone in a WAV recording (used for the test 25 beep A/B). Usage: python3 -I tone_check.py REC.wav"""
import wave,sys,numpy as np
w=wave.open(sys.argv[1]); r=w.readframes(w.getnframes()); a=np.frombuffer(r,dtype='<i2').reshape(-1,2).mean(1)
sr=w.getframerate(); win=4096
hits=[]
for i in range(0,len(a)-win,win//2):
    x=a[i:i+win]*np.hanning(win); X=np.abs(np.fft.rfft(x)); f=np.fft.rfftfreq(win,1/sr)
    band=X[(f>980)&(f<1020)].max(); rest=np.median(X[(f>200)&(f<8000)])+1
    if band/rest>30 and band>1e5: hits.append(round(i/sr,2))
print('length',round(len(a)/sr,1),'s; peak',int(np.abs(a).max()),'; windows with a strong 1 kHz tone:',len(hits), hits[:30])
