package com.runecolor.bridge;

import com.google.gson.Gson;
import okhttp3.OkHttpClient;

/** Publishes one snapshot to the URL in {@code args[0]}, for the loopback test. */
public final class LoopbackMain {
    public static void main(String[] args) throws Exception {
        SnapshotPublisher publisher =
                new SnapshotPublisher(new OkHttpClient(), new Gson(), args[0]);
        publisher.publish(new Snapshot(1, 123456, 1757193600123L, "LOGGED_IN",
                new Snapshot.Stat(42, 55), new Snapshot.Stat(12, 43), 87,
                new Snapshot.Point(3222, 3218, 0)));
        Thread.sleep(2000);
        publisher.close();
    }
}
