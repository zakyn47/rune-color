package com.runecolor.bridge;

import com.google.gson.Gson;
import com.google.inject.Provides;
import lombok.extern.slf4j.Slf4j;
import net.runelite.api.Client;
import net.runelite.api.events.GameTick;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.eventbus.Subscribe;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginDescriptor;
import okhttp3.OkHttpClient;

import javax.inject.Inject;
import java.util.concurrent.TimeUnit;

@Slf4j
@PluginDescriptor(
        name = "RuneColor Bridge",
        description = "Pushes exact player vitals to the RuneColor bot over localhost.",
        enabledByDefault = false
)
public class RuneColorBridgePlugin extends Plugin {
    @Inject
    private Client client;

    @Inject
    private RuneColorBridgeConfig config;

    private SnapshotPublisher publisher;
    private int tickCounter;

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
        tickCounter = 0;
        log.info("RuneColor Bridge started, pushing to port {}.", config.port());
    }

    @Override
    protected void shutDown() {
        if (publisher != null) {
            publisher.close();
            publisher = null;
        }
        log.info("RuneColor Bridge stopped.");
    }

    @Subscribe
    public void onGameTick(GameTick event) {
        // Nothing may escape this method. An exception thrown from an event handler
        // risks the client disabling the plugin mid-session, which would strand a
        // running bot on its OCR fallback without saying why.
        try {
            if (publisher == null) {
                return;
            }
            if (++tickCounter < config.ticksPerPush()) {
                return;
            }
            tickCounter = 0;
            publisher.publish(SnapshotBuilder.build(client, System.currentTimeMillis()));
        } catch (Exception e) {
            log.warn("Skipped a snapshot: {}", e.toString());
        }
    }
}
