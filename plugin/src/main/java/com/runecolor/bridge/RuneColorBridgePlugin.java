package com.runecolor.bridge;

import com.google.gson.Gson;
import com.google.inject.Provides;
import lombok.extern.slf4j.Slf4j;
import net.runelite.api.Client;
import net.runelite.client.callback.ClientThread;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;
import okhttp3.OkHttpClient;

import javax.inject.Inject;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Pushes the player's vitals to the RuneColor bot.
 *
 * <p>Snapshots are driven by our own timer rather than by a {@code @Subscribe} on
 * {@code GameTick}. That is not a preference. When this plugin is side-loaded, its
 * classes live in a {@code PluginClassLoader}, which is a plain {@code URLClassLoader}
 * and does not implement RuneLite's {@code PrivateLookupableClassLoader}. The event
 * bus builds each subscriber with {@code LambdaMetafactory}, that needs a private
 * lookup it cannot obtain across that class loader, and registration fails with
 * "Invalid caller". The plugin still starts, so the only sign of trouble is one
 * warning in the client log and a feed that never sends anything.
 *
 * <p>The timer sidesteps the event bus entirely. It costs exact tick alignment, which
 * this design does not need: the bot asks whether a reading is younger than two ticks,
 * not which tick it came from.
 */
@Slf4j
@PluginDescriptor(
        name = "RuneColor Bridge",
        description = "Pushes exact player vitals to the RuneColor bot over localhost.",
        enabledByDefault = false
)
public class RuneColorBridgePlugin extends Plugin {
    /** One game tick, plus a little, matching `RuneLiteBot.game_tick`. */
    private static final long PERIOD_MS = 603;

    @Inject
    private Client client;

    @Inject
    private ClientThread clientThread;

    @Inject
    private RuneColorBridgeConfig config;

    private SnapshotPublisher publisher;
    private ScheduledExecutorService timer;
    private int cycle;

    @Provides
    RuneColorBridgeConfig provideConfig(ConfigManager configManager) {
        return configManager.getConfig(RuneColorBridgeConfig.class);
    }

    @Override
    protected void startUp() {
        // A short timeout keeps a wedged connection from occupying the single
        // publisher thread for longer than the data stays useful.
        OkHttpClient http = new OkHttpClient.Builder()
                .connectTimeout(500, TimeUnit.MILLISECONDS)
                .readTimeout(500, TimeUnit.MILLISECONDS)
                .writeTimeout(500, TimeUnit.MILLISECONDS)
                .build();
        publisher = new SnapshotPublisher(http, new Gson(),
                "http://127.0.0.1:" + config.port() + "/api/snapshot/");
        cycle = 0;

        timer = Executors.newSingleThreadScheduledExecutor(runnable -> {
            Thread thread = new Thread(runnable, "runecolor-bridge-timer");
            thread.setDaemon(true);
            return thread;
        });
        timer.scheduleAtFixedRate(this::tick, 0, PERIOD_MS, TimeUnit.MILLISECONDS);
        log.info("RuneColor Bridge started, pushing to port {}.", config.port());
    }

    @Override
    protected void shutDown() {
        if (timer != null) {
            timer.shutdownNow();
            timer = null;
        }
        if (publisher != null) {
            publisher.close();
            publisher = null;
        }
        log.info("RuneColor Bridge stopped.");
    }

    /**
     * Hop onto the client thread, take a snapshot, and hand it to the publisher.
     *
     * <p>Nothing may escape this method. It runs on a scheduled executor, where an
     * escaping exception cancels all future runs silently: the feed would simply stop,
     * and the bot would fall back to OCR without ever saying why.
     */
    private void tick() {
        try {
            if (++cycle < config.ticksPerPush()) {
                return;
            }
            cycle = 0;
            // The Client API is only safe to touch on the client thread, so the
            // snapshot is built there and published off it.
            clientThread.invoke(() -> {
                try {
                    SnapshotPublisher current = publisher;
                    if (current != null) {
                        current.publish(SnapshotBuilder.build(
                                client, System.currentTimeMillis()));
                    }
                } catch (Exception e) {
                    log.warn("Skipped a snapshot: {}", e.toString());
                }
            });
        } catch (Exception e) {
            log.warn("Snapshot timer stumbled: {}", e.toString());
        }
    }
}
