import sys, time, threading, urllib.request
sys.path.insert(0, r"S:\Coding Projects\HumToMidi")
if __name__ == "__main__":
    import server; L = server.LIVE
    srv = server.ThreadingHTTPServer(("127.0.0.1", 8799), server.Handler); threading.Thread(target=srv.serve_forever, daemon=True).start()
    t0=time.time(); print(L.set(vol=0.0, snd="keys", stick=1.0)['available'], 'engine process up in %.1f s'%(time.time()-t0))
    L.test_voice(True); print(L.start()['mode'])
    stop = False
    def poll():
        while not stop:
            urllib.request.urlopen("http://127.0.0.1:8799/api/live").read(); time.sleep(0.05)   # 20x/s: much harder than the page
    threading.Thread(target=poll, daemon=True).start()
    def busy():   # and the helper busy with other Python work, like saving a take
        while not stop: sum(i*i for i in range(200000))
    threading.Thread(target=busy, daemon=True).start()
    time.sleep(10); stop = True
    print('with 20 status requests/s + busy helper:', L.timing(), ' playing note', L.status()['note'])
    L.test_voice(False); L.stop(); L.set(vol=0.8); L.close()
