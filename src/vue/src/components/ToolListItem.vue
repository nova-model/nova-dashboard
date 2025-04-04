<!-- Creates a VListItem for launching, opening, and stopping a Galaxy tool. -->
<template>
    <v-list-item>
        <template v-slot:prepend>
            <v-btn
                :href="getURL(tool.id)"
                class="mr-2"
                size="x-small"
                icon
                rounded
                tile
                @click.prevent="setClipboard(getURL(tool.id))"
            >
                <v-icon>mdi-content-copy</v-icon>

                <v-tooltip activator="parent" max-width="300" open-delay="250">
                    <p v-if="linkCopied">Auto-launch link copied!</p>
                    <p v-else>
                        Click to copy a URL that will auto-launch this tool when opened. If you use
                        this tool frequently, you may want to consider creating either a browser
                        bookmark or a desktop shortcut to this link.
                    </p>
                </v-tooltip>
            </v-btn>
        </template>

        <v-list-item-title>{{ tool.name }}</v-list-item-title>
        <v-list-item-subtitle :title="tool.description">
            {{ tool.description }}
        </v-list-item-subtitle>

        <template v-slot:append>
            <v-list-item-action>
                <v-btn v-if="checking_galaxy_login" disabled>Checking login status</v-btn>
                <v-btn v-else-if="!is_logged_in" disabled>Sign in to run apps</v-btn>
                <v-btn v-else-if="!has_monitored" disabled>Checking running tools</v-btn>
                <div v-else>
                    <v-btn v-if="canLaunch(jobs, tool.id)" @click="job.launchJob(tool.id)">
                        Launch
                        <v-icon>mdi-play</v-icon>
                    </v-btn>
                    <v-btn v-if="canUse(jobs, tool.id)" :href="jobs[tool.id]?.url" target="_blank">
                        Open
                        <v-icon>mdi-open-in-new</v-icon>
                    </v-btn>
                    <v-btn
                        v-if="canStop(jobs, tool.id)"
                        color="error"
                        @click="job.stopJob(tool.id)"
                    >
                        Stop
                        <v-icon>mdi-stop</v-icon>
                    </v-btn>

                    <ToolStatus
                        v-if="isChanging(jobs, tool.id)"
                        :state="jobs[tool.id]?.state"
                        :submitted="jobs[tool.id]?.submitted"
                        :url="jobs[tool.id]?.url"
                    />
                </div>
            </v-list-item-action>
        </template>
    </v-list-item>
</template>

<script setup>
import { storeToRefs } from "pinia"
import { ref } from "vue"

import ToolStatus from "@/components/ToolStatus.vue"
import { useJobStore } from "@/stores/job"
import { useUserStore } from "@/stores/user"

const props = defineProps({
    tool: {
        required: true,
        type: Object
    }
})

const job = useJobStore()
const { has_monitored, jobs } = storeToRefs(job)
const user = useUserStore()
const { checking_galaxy_login, is_logged_in } = storeToRefs(user)
const linkCopied = ref(false)

function canLaunch(jobs, tool_id) {
    return !["error", "launching", "launched", "stopping"].includes(jobs[tool_id]?.state)
}

function canUse(jobs, tool_id) {
    return jobs[tool_id]?.state === "launched"
}

function canStop(jobs, tool_id) {
    return ["launched", "error"].includes(jobs[tool_id]?.state)
}

function getURL(tool_id) {
    return window.location.origin + `/launch/${tool_id}`
}

function isChanging(jobs, tool_id) {
    return ["launching", "stopping"].includes(jobs[tool_id]?.state)
}

function setClipboard(text) {
    navigator.clipboard.writeText(text)

    linkCopied.value = true
    setTimeout(() => {
        linkCopied.value = false
    }, 2000)
}
</script>

<style scoped>
.auto-launch-btn {
    min-width: 0;
}
</style>
