<template>
    <v-alert
        tile
        v-if="show"
        :color="statusType === 'resolved' ? 'success' : 'warning'"
        :icon="statusType === 'resolved' ? 'mdi-check-circle' : 'mdi-database-off'"
        lines="one"
        closable
        @click:close="show = false"
    >
        {{ message }}
    </v-alert>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue"

const show = ref(false)
const message = ref("")
const statusType = ref("alert")
const alerts_url = "http://10.64.193.81:32001/api/v1/alerts"
let lastAlertMessage =
    "One or more NDIP services are currently experiencing issues. You may be unable to run tools during this time. If issues persist, please contact the NDIP team."
let pollInterval = null

const checkStatus = async () => {
    try {
        const response = await fetch(alerts_url)
        const result = await response.json()
        console.log(result)
        const alerts = result?.data?.alerts || []

        if (alerts.length > 0) {
            const latestMessage = alerts[0].annotations.title

            if (latestMessage !== lastAlertMessage) {
                message.value = latestMessage
                lastAlertMessage = latestMessage
                statusType.value = "alert"
                show.value = true
            }
        } else if (show.value && statusType.value === "alert") {
            message.value = "All systems are back to normal. Click to dismiss."
            statusType.value = "resolved"

            setTimeout(() => {
                if (statusType.value === resolved) {
                    show.value = false
                    lastAlertMessage = ""
                }
            }, 1000)
        }
    } catch (error) {
        console.error("failed to fetch alerts:", error)
        message.value = "Could not connect to database"
        statusType.value = "alert"
        show.value = true
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
