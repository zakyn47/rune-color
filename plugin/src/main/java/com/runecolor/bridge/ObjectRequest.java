package com.runecolor.bridge;

import java.util.Collections;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;

/**
 * The object IDs the bot last asked for.
 *
 * <p>Written on the publisher thread when a reply arrives, read on the client thread
 * when the next snapshot is built.
 */
public final class ObjectRequest {
    private final AtomicReference<Set<Integer>> ids =
            new AtomicReference<>(Collections.emptySet());

    void update(BotReply reply) {
        ids.set(reply.objects);
    }

    Set<Integer> ids() {
        return ids.get();
    }
}
