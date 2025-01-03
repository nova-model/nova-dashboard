<!-- Defines the content that should be loaded regardless of what route the user is viewing. -->
<template>
    <v-app>
        <v-main>
            <v-app-bar>
                <v-app-bar-title class="cursor-pointer flex-0-1 mr-1" @click="$router.push('/')">
                    Neutrons Application Dashboard
                </v-app-bar-title>

                <v-btn size="x-small" icon>
                    <v-icon>mdi-information-outline</v-icon>

                    <v-menu activator="parent" :close-on-content-click="false" open-on-hover>
                        <v-card width="600">
                            <v-card-title class="mb-2 px-0">About This Dashboard</v-card-title>
                            <v-card-text class="pa-0">
                                <p class="mb-2">
                                    This dashboard has been developed as a part of the NOVA LDRD
                                    project. It is meant to serve as a way to launch and manage
                                    interactive applications running in
                                    <a :href="galaxy_url" target="_blank">Galaxy</a>.
                                </p>

                                <p>The dashboard is currently running version {{ version }}.</p>
                            </v-card-text>
                        </v-card>
                    </v-menu>
                </v-btn>

                <v-spacer />

                <ActiveToolsPanel class="mr-4" />

                <span v-if="is_logged_in" class="pr-2 text-button">Welcome, {{ given_name }}</span>
                <v-btn v-else>
                    Sign In

                    <v-menu activator="parent">
                        <v-list>
                            <v-list-item :href="ucams_auth_url">via UCAMS</v-list-item>
                            <v-list-item :href="xcams_auth_url">via XCAMS</v-list-item>
                        </v-list>
                    </v-menu>
                </v-btn>

                <v-btn v-if="is_logged_in" icon>
                    <v-icon>mdi-cogs</v-icon>

                    <v-menu activator="parent" :close-on-content-click="false">
                        <v-card width="400">
                            <v-card-title>Preferences</v-card-title>

                            <v-card-text>
                                <v-switch
                                    v-model="autoopen"
                                    label="Automatically Open Tools in a New Tab After Launch"
                                    hide-details
                                    @click="user.toggleAutoopen()"
                                />
                                <p class="text-caption">
                                    If tools don't automatically open after launching, then you may
                                    need to allow pop-ups on this site in your browser or browser
                                    extension settings.
                                </p>
                            </v-card-text>
                        </v-card>
                    </v-menu>
                </v-btn>
            </v-app-bar>

            <RouterView v-if="user.ready" />

            <v-footer class="justify-center my-0 px-1 py-0 text-center" app border>
                <v-progress-circular
                    :indeterminate="running"
                    class="mr-1"
                    color="primary"
                    size="16"
                    width="3"
                />
                <a
                    :href="galaxy_url"
                    class="text-grey-lighten-1 text-caption text-decoration-none"
                    target="_blank"
                >
                    Powered by Calvera
                </a>
                <v-spacer />
                <a
                    href="https://www.ornl.gov/"
                    class="text-grey-lighten-1 text-caption text-decoration-none"
                    target="_blank"
                >
                    © 2024 ORNL
                </a>
            </v-footer>
            <v-dialog v-model="user.requires_galaxy_login" persistent width="400">
                <v-card class="text-center">
                    <v-card-text>
                        In order to use this dashboard, you will need to complete a one-time login
                        to Calvera. Please go to
                        <a target="_blank" :href="galaxy_url">{{ galaxy_url }}</a> and log into
                        Calvera using your {{ user.login_type }} credentials.
                    </v-card-text>
                    <v-card-actions class="justify-center">
                        <v-btn width="200" margin="auto" @click="stopLoginPrompt"
                            >Cancel Login</v-btn
                        >
                    </v-card-actions>
                </v-card>
            </v-dialog>
        </v-main>
    </v-app>
</template>

<script setup>
import { onMounted } from "vue"
import { storeToRefs } from "pinia"
import { RouterView } from "vue-router"

import ActiveToolsPanel from "@/components/ActiveToolsPanel.vue"
import { useJobStore } from "@/stores/job"
import { useUserStore } from "@/stores/user"

const job = useJobStore()
const { running } = storeToRefs(job)
const user = useUserStore()
const { autoopen, given_name, is_logged_in, ucams_auth_url, xcams_auth_url } = storeToRefs(user)
const galaxy_url = import.meta.env.VITE_GALAXY_URL
const version = import.meta.env.VITE_DASHBOARD_VERSION

onMounted(async () => {
    await user.getUser()
    user.getAutoopen()

    if (user.is_logged_in) {
        await user.userStatus()

        if (user.requires_galaxy_login) {
            user.userMonitorLogin()
        }
    }
})

function stopLoginPrompt() {
    user.resetUser()
}
</script>
