package com.runecolor.bridge;

import com.google.gson.Gson;
import okhttp3.Interceptor;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Protocol;
import okhttp3.Response;
import okhttp3.ResponseBody;
import org.junit.Test;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

public class SnapshotPublisherTest {
    private static Snapshot sample() {
        return new Snapshot(1, 5, 99L, "LOGGED_IN",
                new Snapshot.Stat(42, 55), new Snapshot.Stat(12, 43), 87,
                new Snapshot.Point(3222, 3218, 0));
    }

    @Test
    public void postsTheSnapshotAsJson() throws Exception {
        BlockingQueue<String> received = new ArrayBlockingQueue<>(1);
        try (ServerSocket server = new ServerSocket(0)) {
            Thread sink = new Thread(() -> {
                try (Socket socket = server.accept()) {
                    BufferedReader reader = new BufferedReader(
                            new InputStreamReader(socket.getInputStream()));
                    StringBuilder request = new StringBuilder();
                    String line;
                    int contentLength = 0;
                    while ((line = reader.readLine()) != null && !line.isEmpty()) {
                        request.append(line).append('\n');
                        if (line.toLowerCase().startsWith("content-length:")) {
                            contentLength =
                                    Integer.parseInt(line.split(":")[1].trim());
                        }
                    }
                    char[] body = new char[contentLength];
                    int read = 0;
                    while (read < contentLength) {
                        read += reader.read(body, read, contentLength - read);
                    }
                    request.append(new String(body));
                    OutputStream out = socket.getOutputStream();
                    out.write("HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
                            .getBytes("UTF-8"));
                    out.flush();
                    received.offer(request.toString());
                } catch (Exception ignored) {
                    // The test asserts on the queue; a failure here shows up as a
                    // timeout below.
                }
            });
            sink.setDaemon(true);
            sink.start();

            SnapshotPublisher publisher = new SnapshotPublisher(
                    new OkHttpClient(), new Gson(),
                    "http://127.0.0.1:" + server.getLocalPort() + "/api/snapshot/");
            publisher.publish(sample());

            String request = received.poll(5, TimeUnit.SECONDS);
            publisher.close();

            assertNotNull("no request arrived", request);
            assertTrue(request.startsWith("POST /api/snapshot/"));
            assertTrue(request.contains("\"schema\":1"));
            assertTrue(request.contains("\"run_energy\":87"));
            assertTrue(request.contains("\"world_point\""));
            assertTrue(request.contains("\"sent_at\":99"));
        }
    }

    @Test
    public void survivesAConnectionRefusal() throws Exception {
        int deadPort;
        try (ServerSocket probe = new ServerSocket(0)) {
            deadPort = probe.getLocalPort();
        }

        SnapshotPublisher publisher = new SnapshotPublisher(
                new OkHttpClient(), new Gson(),
                "http://127.0.0.1:" + deadPort + "/api/snapshot/");

        // Nobody is listening: this is the common case, not an error, and it must
        // neither throw nor block the caller.
        for (int i = 0; i < 20; i++) {
            publisher.publish(sample());
        }
        Thread.sleep(500);
        publisher.close();
    }

    @Test
    public void doesNotQueueABacklog() throws Exception {
        // The bound (ArrayBlockingQueue capacity one) makes queueSize() <= 1
        // trivially true no matter how fast the single worker drains it, so this
        // test wouldn't actually exercise drop-oldest unless the worker is kept
        // busy while the flood happens. A real dead-port connection attempt could
        // fail fast enough (immediate ECONNREFUSED on loopback on some platforms)
        // that the worker races ahead and empties the queue between iterations,
        // making the assertion pass without ever having queued a backlog. Instead,
        // wire in an OkHttpClient whose interceptor deterministically parks the
        // worker thread on a latch we control, so it cannot drain anything until we
        // say so.
        CountDownLatch releaseWorker = new CountDownLatch(1);
        Interceptor blockUntilReleased = chain -> {
            try {
                releaseWorker.await(5, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            throw new IOException("test double: no real call is made");
        };
        OkHttpClient blockingClient = new OkHttpClient.Builder()
                .addInterceptor(blockUntilReleased)
                .build();

        SnapshotPublisher publisher = new SnapshotPublisher(
                blockingClient, new Gson(), "http://127.0.0.1:1/api/snapshot/");
        try {
            // Whichever of these publish() calls the worker picks up first will
            // block it (via the interceptor above) for the rest of the test, so
            // every remaining call must compete for the single queue slot.
            for (int i = 0; i < 1000; i++) {
                publisher.publish(sample());
            }
            assertTrue("queue must stay bounded", publisher.queueSize() <= 1);
        } finally {
            releaseWorker.countDown();
            publisher.close();
        }
    }

    /**
     * Not one of the brief's three tests. The brief's log-latch javadoc promises
     * "first failure logs; further failures stay silent until a success resets the
     * latch," but none of the three given tests pins that behavior: they only check
     * that publish() doesn't throw or block, not how many times a failure is
     * actually logged. This test scripts a fail/fail/succeed/fail sequence of
     * responses through an interceptor (rather than mocking OkHttp's call machinery
     * directly) and asserts on {@link SnapshotPublisher#failureLogCallCount()} — a
     * package-private counter added purely for this test, parallel in spirit to the
     * existing package-private {@code toJson()}/{@code queueSize()} seams — since
     * the existing {@code failureLogged} flag alone can't distinguish "logged once"
     * from "logged twice."
     */
    @Test
    public void logsOnlyTheFirstFailureUntilASuccessResetsTheLatch() throws Exception {
        boolean[] succeeds = {false, false, true, false};
        int[] callIndex = {0};
        BlockingQueue<Object> completions = new LinkedBlockingQueue<>();
        Interceptor scripted = chain -> {
            try {
                boolean succeed = succeeds[callIndex[0]++];
                if (succeed) {
                    return new Response.Builder()
                            .request(chain.request())
                            .protocol(Protocol.HTTP_1_1)
                            .code(200)
                            .message("OK")
                            .body(ResponseBody.create(MediaType.get("text/plain"), ""))
                            .build();
                }
                throw new IOException("simulated failure");
            } finally {
                completions.offer(Boolean.TRUE);
            }
        };
        OkHttpClient scriptedClient =
                new OkHttpClient.Builder().addInterceptor(scripted).build();

        SnapshotPublisher publisher = new SnapshotPublisher(
                scriptedClient, new Gson(), "http://127.0.0.1:1/api/snapshot/");
        try {
            publisher.publish(sample());
            assertNotNull("call 1 did not complete", completions.poll(2, TimeUnit.SECONDS));
            awaitFailureLogCount(publisher, 1);

            publisher.publish(sample());
            assertNotNull("call 2 did not complete", completions.poll(2, TimeUnit.SECONDS));
            awaitFailureLogCount(publisher, 1); // second consecutive failure: silent

            publisher.publish(sample());
            assertNotNull("call 3 did not complete", completions.poll(2, TimeUnit.SECONDS));
            awaitFailureLogCount(publisher, 1); // a success logs nothing new

            publisher.publish(sample());
            assertNotNull("call 4 did not complete", completions.poll(2, TimeUnit.SECONDS));
            awaitFailureLogCount(publisher, 2); // failure after success: latch reset, logs again
        } finally {
            publisher.close();
        }
    }

    /**
     * Polls for up to two seconds because the call's completion (observed via the
     * interceptor above) races the few instructions in {@code SnapshotPublisher}
     * that run after {@code Call.execute()} returns and update the counter.
     */
    private static void awaitFailureLogCount(SnapshotPublisher publisher, int expected)
            throws InterruptedException {
        long deadline = System.currentTimeMillis() + 2000;
        while (System.currentTimeMillis() < deadline
                && publisher.failureLogCallCount() != expected) {
            Thread.sleep(10);
        }
        assertEquals(expected, publisher.failureLogCallCount());
    }
}
