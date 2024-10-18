<!-- Defines the content when the user is on the landing page. -->
<template>
    <v-container class="align-start d-flex justify-center mt-16">
        <v-card width="1280">
            <v-card-title class="text-center">
                Welcome to the Neutrons Application Dashboard
            </v-card-title>

            <v-card-text>
                <p class="text-center">
                    You can view the different categories of tools available below. Simply click on
                    a category to access its tools.
                </p>

                <v-container>
                    <v-row>
                        <v-col v-for="(tool, key) in props.tools" :key="key" cols="12" lg="4">
                            <v-card
                                :to="`/${key}`"
                                class="d-flex fill-height flex-column justify-center"
                            >
                                <v-card-item>
                                    <v-card-title class="mb-1">{{ tool.name }}</v-card-title>
                                    <v-card-subtitle>{{ tool.description }}</v-card-subtitle>
                                    <template v-slot:append>
                                        <v-icon>mdi-open-in-app</v-icon>
                                    </template>
                                </v-card-item>
                            </v-card>
                        </v-col>
                    </v-row>
                </v-container>
            </v-card-text>
        </v-card>
    </v-container>
    <v-dialog v-model="user.requires_galaxy_login" persistent width="400">
        <v-card class="text-center">
            <v-card-text>
                In order to use this dashboard, you will need to complete a one-time login to
                Calvera. Please go to <a target="_blank" :href="galaxy_url">{{ galaxy_url }}</a> and
                log into Calvera using your {{ user.login_type }} credentials.
            </v-card-text>
            <v-card-actions class="justify-center">
                <v-btn width="200" margin="auto" @click="stopLoginPrompt">Cancel Login</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup>
import { onMounted } from "vue"
import { useRouter } from "vue-router"

import { useJobStore } from "@/stores/job"
import { useUserStore } from "@/stores/user"

const props = defineProps({
    tools: {
        required: true,
        type: Object
    }
})

const router = useRouter()
const job = useJobStore()
const user = useUserStore()
const galaxy_url = import.meta.env.VITE_GALAXY_URL;

onMounted(async () => {
    await user.getUser()
    user.getAutoopen()
    if (user.is_logged_in) {
        await user.userStatus()
        if (user.requires_galaxy_login) {
            user.userMonitorLogin();
        }
        job.startMonitor(user)
        const lastpath = window.localStorage.getItem("lastpath")
        const redirect = window.localStorage.getItem("redirect")

        if (lastpath !== null && redirect === "true") {
            // The user has just logged in, so we need to redirect them to the last page they were on.
            window.localStorage.removeItem("lastpath")
            window.localStorage.removeItem("redirect")

            router.push(lastpath)
        }
    } else {
        window.localStorage.removeItem("lastpath")
        window.localStorage.setItem("redirect", true)
    }
})

function stopLoginPrompt() {
    user.resetUser();
}
</script>
