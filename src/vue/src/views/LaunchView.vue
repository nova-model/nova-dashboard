<template>
    <v-container class="align-start d-flex justify-center mt-4 text-center">
        <v-card width="1280">
            <v-card-title v-if="targetTool !== null" class="mb-8">
                {{ targetTool?.name }}
            </v-card-title>

            <v-banner v-if="job.galaxy_error" class="bg-error">
                {{ job.galaxy_error }}
            </v-banner>
            <v-card-text v-else>
                <!-- Login required -->
                <div v-if="!checking_galaxy_login && !is_logged_in">
                    <p class="mb-2">You must log in before your tool can be launched.</p>

                    <div>
                        <v-btn :href="ucams_auth_url" class="mr-2">UCAMS</v-btn>
                        <v-btn :href="xcams_auth_url">XCAMS</v-btn>
                    </div>
                </div>
                <div v-else>
                    <!-- Tool does not exist -->
                    <div v-if="targetTool === null">
                        <p>No tool with id "{{ route.params.tool }}" could be found.</p>
                    </div>
                    <!-- Looking for a job in Galaxy -->
                    <div v-else-if="checking_galaxy_login || !foundInGalaxy">
                        <v-progress-circular indeterminate />
                    </div>
                    <!-- Galaxy job was found -->
                    <div v-else-if="targetJob !== null">
                        <div v-if="targetJob.state === 'launched'">
                            <p class="mb-2">Your tool is ready to be used.</p>
                            <v-btn :href="targetJob.url" target="_blank">
                                Open
                                <v-icon>mdi-open-in-new</v-icon>
                            </v-btn>
                        </div>
                        <p v-else-if="targetJob.state === 'stopped'">Your tool has been stopped.</p>
                        <ToolStatus
                            v-else
                            :state="targetJob.state"
                            :submitted="targetJob.submitted"
                            :url="targetJob.url"
                        />
                    </div>
                </div>
            </v-card-text>
        </v-card>
    </v-container>
</template>

<script setup>
import { storeToRefs } from "pinia"
import { onMounted, ref } from "vue"
import { useRoute } from "vue-router"

import ToolStatus from "@/components/ToolStatus.vue"
import { useJobStore } from "@/stores/job"
import { useUserStore } from "@/stores/user"

const props = defineProps({
    tools: {
        required: true,
        type: Object
    }
})

const job = useJobStore()
const { jobs } = storeToRefs(job)
const user = useUserStore()
const { checking_galaxy_login, is_logged_in, ucams_auth_url, xcams_auth_url } = storeToRefs(user)
const route = useRoute()

const foundInGalaxy = ref(false)
const hasLaunched = ref(false) // This is used to avoid launching the tool again if they stop it while on this page.
const launching = ref(false)
const targetJob = ref(null)
const targetTool = ref(null)

function findTargetJob() {
    if (!is_logged_in || checking_galaxy_login.value || targetTool.value === null) {
        return
    }

    for (const id in jobs.value) {
        if (id === targetTool.value.id && jobs.value[id].state !== "stopped") {
            foundInGalaxy.value = true
            targetJob.value = jobs.value[id]
        }
    }

    // We are logged in, the tool has been confirmed to exist, and we didn't find any job for it in Galaxy,
    // so we can launch it here.
    if (targetJob.value === null && !hasLaunched.value && !launching.value) {
        job.launchJob(targetTool.value.id)
        launching.value = true
        hasLaunched.value = true
    }
}

function findTargetTool() {
    for (const key in props.tools) {
        const toolList = props.tools[key].tools
        toolList.forEach((tool) => {
            if (tool.id === route.params.tool) {
                targetTool.value = tool
            }
        })
    }
}

onMounted(async () => {
    findTargetTool()

    job.startMonitor(user, findTargetJob)
    if (!user.is_logged_in) {
        window.localStorage.setItem("lastpath", route.path)
        window.localStorage.setItem("redirect", true)
    }
})
</script>
