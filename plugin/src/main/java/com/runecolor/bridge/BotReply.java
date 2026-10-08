package com.runecolor.bridge;

import com.google.gson.Gson;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** The bot's reply to a snapshot: the profile it wants and the objects to report. */
public final class BotReply {
    static final BotReply EMPTY = new BotReply(null, Collections.emptySet());

    public final ProfileRequest profile;
    public final Set<Integer> objects;

    BotReply(ProfileRequest profile, Set<Integer> objects) {
        this.profile = profile;
        this.objects = objects;
    }

    /** Never throws: it runs on the publisher thread. Anything unreadable asks for nothing. */
    static BotReply parse(Gson gson, String body) {
        Wire wire;
        try {
            wire = gson.fromJson(body, Wire.class);
        } catch (RuntimeException e) {
            return EMPTY;
        }
        if (wire == null) {
            return EMPTY;
        }
        return new BotReply(wire.profile, ids(wire.objects));
    }

    private static Set<Integer> ids(List<Integer> objects) {
        if (objects == null) {
            return Collections.emptySet();
        }
        Set<Integer> ids = new HashSet<>();
        for (Integer id : objects) {
            if (id != null) {
                ids.add(id);
            }
        }
        return Collections.unmodifiableSet(ids);
    }

    private static final class Wire {
        ProfileRequest profile;
        List<Integer> objects;
    }
}
