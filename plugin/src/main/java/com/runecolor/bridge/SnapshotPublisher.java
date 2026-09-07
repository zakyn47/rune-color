package com.runecolor.bridge;

import com.google.gson.Gson;
import lombok.extern.slf4j.Slf4j;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Serializes snapshots and POSTs them to the bot.
 *
 * <p>Publishing is fire-and-forget on a queue of capacity one. If the path stalls,
 * the bot should receive the newest snapshot, never a replayed backlog of stale
 * ones, so a full queue drops the oldest entry rather than blocking or growing.
 *
 * <p>Nobody listening is the normal state: the plugin runs whenever RuneLite does,
 * while the bot's server runs only while a script runs. A connection refusal is
 * therefore logged once and then silenced until a success resets the latch, so the
 * client log does not gain a line every 600 ms forever.
 */
@Slf4j
public class SnapshotPublisher {
    private static final MediaType JSON = MediaType.get("application/json");

    private final OkHttpClient http;
    private final Gson gson;
    private final String url;
    private final ArrayBlockingQueue<Runnable> queue = new ArrayBlockingQueue<>(1);
    private final ThreadPoolExecutor executor;
    private final AtomicBoolean failureLogged = new AtomicBoolean(false);

    // Test-only observability: counts how many times a failure was actually logged,
    // as opposed to failureLogged above (which only tells us the latch's current
    // state, not how many times the log statement itself ran). Package-private, in
    // the same spirit as toJson()/queueSize() below, purely so SnapshotPublisherTest
    // can pin the "first failure logs, further failures stay silent until a success
    // resets the latch" behavior without duplicating a logging framework here.
    private final AtomicInteger failureLogCallCount = new AtomicInteger(0);

    public SnapshotPublisher(OkHttpClient http, Gson gson, String url) {
        this.http = http;
        this.gson = gson;
        this.url = url;
        this.executor = new ThreadPoolExecutor(1, 1, 0L, TimeUnit.MILLISECONDS, queue,
                runnable -> {
                    Thread thread = new Thread(runnable, "runecolor-bridge-publisher");
                    thread.setDaemon(true);
                    return thread;
                },
                new ThreadPoolExecutor.DiscardOldestPolicy());
    }

    String toJson(Snapshot snapshot) {
        return gson.toJson(snapshot);
    }

    int queueSize() {
        return queue.size();
    }

    int failureLogCallCount() {
        return failureLogCallCount.get();
    }

    /** Hand a snapshot off for delivery. Never blocks, never throws. */
    public void publish(Snapshot snapshot) {
        final String body;
        try {
            body = toJson(snapshot);
        } catch (RuntimeException e) {
            logFailureOnce("Could not serialize a snapshot", e);
            return;
        }

        try {
            executor.execute(() -> send(body));
        } catch (RuntimeException e) {
            // Rejected because the executor is shutting down. Nothing to do.
            log.debug("Snapshot dropped: {}", e.toString());
        }
    }

    private void send(String body) {
        // Building the request has to sit inside the try as well. A malformed URL
        // makes Request.Builder throw, and an exception escaping this method kills
        // the publisher thread without a word, leaving the bot to wonder why nothing
        // ever arrives.
        try {
            Request request = new Request.Builder()
                    .url(url)
                    .post(RequestBody.create(JSON, body))
                    .build();
            try (Response response = http.newCall(request).execute()) {
                if (response.isSuccessful()) {
                    failureLogged.set(false);
                } else {
                    logFailureOnce("Bot rejected a snapshot: HTTP " + response.code(),
                            null);
                }
            }
        } catch (Exception e) {
            logFailureOnce("Could not reach the bot", e);
        }
    }

    private void logFailureOnce(String message, Exception cause) {
        if (failureLogged.compareAndSet(false, true)) {
            failureLogCallCount.incrementAndGet();
            log.info("{} ({}). Further failures stay silent until one succeeds.",
                    message, cause == null ? "no exception" : cause.toString());
        }
    }

    public void close() {
        executor.shutdownNow();
    }
}
