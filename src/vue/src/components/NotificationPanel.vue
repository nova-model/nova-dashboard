<template>
    <v-btn size="x-small" icon>
        <v-icon>mdi-bell</v-icon>

        <v-menu activator="parent" :close-on-content-click="false" open-on-hover>
            <v-card max-width="800">
                <v-card-title class="mb-2 px-0">Set System Notification</v-card-title>

                <v-card-text class="px-0">
                    <v-switch v-model="display" label="Display?" />
                    <v-textarea
                        v-model="message"
                        label="Change Notification"
                        rows="1"
                        width="300"
                        auto-grow
                        outlined
                    />
                </v-card-text>

                <v-card-actions class="px-0">
                    <v-btn color="primary" @click="notification.set">Save</v-btn>
                </v-card-actions>
            </v-card>
        </v-menu>
    </v-btn>
</template>

<script setup>
import { storeToRefs } from "pinia"
import { onBeforeUnmount, onMounted } from "vue"

import { useNotificationStore } from "@/stores/notification"

const notification = useNotificationStore()
const { display, message } = storeToRefs(notification)
let pollInterval = null

onMounted(async () => {
    notification.read()
    pollInterval = setInterval(notification.read, 60000)
})

onBeforeUnmount(() => {
    clearInterval(pollInterval)
})
</script>

<style scoped>
.notification-message {
    white-space: pre-wrap;
}
</style>
