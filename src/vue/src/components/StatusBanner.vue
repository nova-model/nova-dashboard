<template>
    <v-alert
        v-if="show"
        :color="alertColor"
        :icon="alertIcon"
        lines="one"
        closable
        tile
        @click:close="show = false"
    >
        <p>{{ alertTitle }}</p>

        <v-expansion-panels class="w-25" v-if="alerts.length > 0">
            <v-expansion-panel color="warning" elevation="0" title="View Alerts" tile>
                <template v-slot:text>
                    <v-list bg-color="warning">
                        <v-list-item
                            v-for="alert in alerts"
                            :title="alert?.annotations?.title"
                            :subtitle="alert?.annotations?.description"
                        />
                    </v-list>
                </template>
            </v-expansion-panel>
        </v-expansion-panels>
    </v-alert>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from "vue"

const show = ref(false)
const statusType = ref("alert")
const alerts = ref([])
const alertsUrl = "http://10.64.193.81:32001/api/v1/alerts"
const alertColor = computed(() => (statusType.value === "resolved" ? "success" : "warning"))
const alertIcon = computed(() =>
    statusType.value === "resolved" ? "mdi-check-circle" : "mdi-database-off"
)
const alertTitle = computed(() => {
    if (statusType.value === "resolved") {
        return "All systems are back to normal. Click to dismiss."
    } else {
        return "One or more NDIP services are currently experiencing issues. You may be unable to run tools during this time. If issues persist, please contact the NDIP team."
    }
})
let lastAlertMessage = ""

let pollInterval = null

const checkStatus = async () => {
    try {
        const response = await fetch(alertsUrl)
        const result = await response.json()
        alerts.value = result?.data?.alerts || []

        if (alerts.value.length > 0) {
            const latestMessage = alerts.value[0]?.annotations?.description || ""

            if (latestMessage !== lastAlertMessage) {
                lastAlertMessage = latestMessage
                statusType.value = "alert"
                show.value = true
            }
        } else if (show.value && statusType.value === "alert") {
            alerts.value = []
            lastAlertMessage = ""
            statusType.value = "resolved"
        } else {
            alerts.value = []
            lastAlertMessage = ""
            show.value = false
        }
    } catch (error) {
        console.error("Failed to retrieve NDIP service status:", error)
        alerts.value = [
            {
                annotations: {
                    title: "Failed to retrieve NDIP service status."
                }
            }
        ]
        show.value = true
        statusType.value = "alert"
    }
}

onMounted(() => {
    checkStatus()
    pollInterval = setInterval(checkStatus, 60000)
})

onBeforeUnmount(() => {
    clearInterval(pollInterval)
})
</script>

<style>
.v-expansion-panel-text__wrapper {
    padding: 0 !important;
}
</style>
