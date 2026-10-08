package com.runecolor.bridge;

import com.google.gson.Gson;
import org.junit.Test;

import java.util.Arrays;
import java.util.HashSet;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

public class BotReplyTest {
    private static BotReply parse(String body) {
        return BotReply.parse(new Gson(), body);
    }

    @Test
    public void readsTheProfileAndObjects() {
        BotReply reply = parse("{\"profile\":{\"name\":\"X\",\"path\":\"p\"},"
                + "\"objects\":[11361,11360,11361]}");
        assertEquals("X", reply.profile.name);
        assertEquals(new HashSet<>(Arrays.asList(11360, 11361)), reply.objects);
    }

    @Test
    public void missingObjectsMeansNone() {
        assertTrue(parse("{\"profile\":null}").objects.isEmpty());
    }

    @Test
    public void malformedBodyAsksForNothing() {
        BotReply reply = parse("Snapshot received.");
        assertNull(reply.profile);
        assertTrue(reply.objects.isEmpty());
    }

    @Test
    public void malformedObjectsAsksForNothing() {
        assertTrue(parse("{\"objects\":[\"rock\"]}").objects.isEmpty());
    }

    @Test
    public void theRequestHoldsTheLatestReply() {
        ObjectRequest request = new ObjectRequest();
        assertTrue(request.ids().isEmpty());
        request.update(parse("{\"objects\":[11361]}"));
        assertEquals(new HashSet<>(Arrays.asList(11361)), request.ids());
        request.update(parse("{}"));
        assertTrue(request.ids().isEmpty());
    }
}
