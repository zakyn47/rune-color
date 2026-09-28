package com.runecolor.bridge;

import com.google.gson.Gson;
import lombok.extern.slf4j.Slf4j;

import java.io.File;
import java.util.concurrent.Executor;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Switches the client to the profile the bot asks for in its snapshot replies.
 *
 * <p>The bot states its wish on every reply, so this sees the same request about
 * twice a second. It acts only when the wanted profile is not the active one, never
 * runs two switches at once, and does not retry a file that failed until the bot asks
 * for something else, so a broken file cannot turn into a switch loop.
 */
@Slf4j
public class ProfileSwitcher {
    private final ProfileStore store;
    private final Executor executor;
    private final Gson gson;
    private final AtomicBoolean inFlight = new AtomicBoolean(false);
    private volatile ProfileRequest failed;

    public ProfileSwitcher(ProfileStore store, Executor executor, Gson gson) {
        this.store = store;
        this.executor = executor;
        this.gson = gson;
    }

    /** Act on one reply body. Never throws: it runs on the publisher thread. */
    public void onReply(String body) {
        ProfileRequest wanted = parse(body);
        if (wanted != null && wanted.equals(failed)) {
            return;
        }
        failed = null;
        if (wanted == null || !wanted.isComplete()
                || wanted.name.equals(store.activeName())) {
            return;
        }
        if (!inFlight.compareAndSet(false, true)) {
            return;
        }
        try {
            executor.execute(() -> apply(wanted));
        } catch (RuntimeException e) {
            inFlight.set(false);
            log.debug("Profile switch not scheduled: {}", e.toString());
        }
    }

    private ProfileRequest parse(String body) {
        try {
            Reply reply = gson.fromJson(body, Reply.class);
            return reply == null ? null : reply.profile;
        } catch (RuntimeException e) {
            return null;
        }
    }

    private void apply(ProfileRequest wanted) {
        try {
            store.apply(wanted.name, new File(wanted.path));
            log.info("Switched to RuneLite profile {}.", wanted.name);
        } catch (Exception | LinkageError e) {
            // LinkageError too: a RuneLite update that changes the profile API
            // would otherwise kill this thread without a line in the client log.
            failed = wanted;
            log.warn("Could not switch to RuneLite profile {} from {}: {}",
                    wanted.name, wanted.path, e.toString());
        } finally {
            inFlight.set(false);
        }
    }

    private static final class Reply {
        ProfileRequest profile;
    }
}
