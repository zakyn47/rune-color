package com.runecolor.bridge;

import com.google.gson.Gson;
import org.junit.Test;

import java.io.File;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Queue;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class ProfileSwitcherTest {
    private static final String WANT_X =
            "{\"profile\":{\"name\":\"RuneColor - X\",\"path\":\"C:/p/x.properties\"}}";

    private static final class FakeStore implements ProfileStore {
        String active = "Mine";
        boolean fail;
        final List<String> applied = new ArrayList<>();

        @Override
        public String activeName() {
            return active;
        }

        @Override
        public void apply(String name, File file) throws Exception {
            applied.add(name + "@" + file.getPath());
            if (fail) {
                throw new Exception("broken file");
            }
            active = name;
        }
    }

    @Test
    public void switchesWhenTheWantedProfileIsNotActive() {
        FakeStore store = new FakeStore();
        new ProfileSwitcher(store, Runnable::run, new Gson()).onReply(WANT_X);
        assertEquals(1, store.applied.size());
        assertTrue(store.applied.get(0).startsWith("RuneColor - X@"));
        assertEquals("RuneColor - X", store.active);
    }

    @Test
    public void doesNothingWhenTheProfileIsAlreadyActive() {
        FakeStore store = new FakeStore();
        store.active = "RuneColor - X";
        new ProfileSwitcher(store, Runnable::run, new Gson()).onReply(WANT_X);
        assertTrue(store.applied.isEmpty());
    }

    @Test
    public void ignoresANullProfile() {
        FakeStore store = new FakeStore();
        new ProfileSwitcher(store, Runnable::run, new Gson()).onReply("{\"profile\":null}");
        assertTrue(store.applied.isEmpty());
    }

    @Test
    public void ignoresAReplyFromABotThatPredatesProfiles() {
        FakeStore store = new FakeStore();
        new ProfileSwitcher(store, Runnable::run, new Gson()).onReply("Snapshot received.");
        assertTrue(store.applied.isEmpty());
    }

    @Test
    public void doesNotRetryAFailedFileUntilTheRequestChanges() {
        FakeStore store = new FakeStore();
        store.fail = true;
        ProfileSwitcher switcher = new ProfileSwitcher(store, Runnable::run, new Gson());
        switcher.onReply(WANT_X);
        switcher.onReply(WANT_X);
        assertEquals(1, store.applied.size());

        switcher.onReply("{\"profile\":null}");
        switcher.onReply(WANT_X);
        assertEquals(2, store.applied.size());
    }

    @Test
    public void ignoresRepeatsWhileASwitchIsInFlight() {
        FakeStore store = new FakeStore();
        Queue<Runnable> pending = new ArrayDeque<>();
        ProfileSwitcher switcher = new ProfileSwitcher(store, pending::add, new Gson());
        switcher.onReply(WANT_X);
        switcher.onReply(WANT_X);
        assertEquals(1, pending.size());
        pending.remove().run();
        assertEquals(1, store.applied.size());
    }
}
