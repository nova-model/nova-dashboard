<!-- Defines the content that should be loaded regardless of what route the user is viewing. -->
<template>
    <v-app>
        <v-main>
            <v-app-bar elevation="0">
                <v-app-bar-title class="cursor-pointer flex-0-1 mr-1" @click="$router.push('/')">
                    <v-img alt="NOVA Logo" src="/logo_bw.png" width="200" />
                </v-app-bar-title>

                <InfoPanel />
                <NotificationPanel ref="notificationPanel" v-show="is_admin" />

                <a :href="galaxyUrl" class="ml-4 text-decoration-none text-white" target="_blank">
                    {{ galaxyAlias }}
                </a>
                <span class="mx-1">&middot;</span>
                <a :href="novaDocsUrl" class="text-decoration-none text-white" target="_blank">
                    {{ novaAlias }} Documentation
                </a>
                <span class="mx-1">&middot;</span>
                <a :href="novaTutorialUrl" class="text-decoration-none text-white" target="_blank">
                    {{ novaAlias }} Tutorial
                </a>
                <span class="mx-1">&middot;</span>
                <a :href="galaxyDocsUrl" class="text-decoration-none text-white" target="_blank">
                    Admin Guide
                </a>

                <v-spacer />

                <ActiveToolsPanel class="mr-4" />

                <span v-if="is_logged_in" class="pr-2 text-button">
                    Welcome, {{ given_name }}
                </span>
                <v-btn v-else-if="!route.path.startsWith('/launch')">
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

                <v-btn v-if="is_logged_in" icon>
                    <v-icon>mdi-account-circle</v-icon>

                    <v-menu activator="parent">
                        <v-list>
                            <v-list-item prepend-icon="mdi-logout" @click="logout">
                                Logout
                            </v-list-item>
                        </v-list>
                    </v-menu>
                </v-btn>
            </v-app-bar>

            <StatusPanel />
            <v-banner
                v-if="
                    notificationPanel &&
                    notificationPanel.displayNotification &&
                    notificationPanel.notificationMessage
                "
                class="bg-warning justify-center py-0"
            >
                <v-icon class="mr-1">mdi-information-outline</v-icon>
                {{ notificationPanel.notificationMessage }}
            </v-banner>

            <v-fab
                v-if="
                    (genericTools?.tools?.length > 0 ||
                        genericTools?.prototype_tools?.length > 0) &&
                    !drawer
                "
                location="right center"
                app
                icon
                @click="toggleDrawer"
            >
                <v-icon>mdi-tools</v-icon>
                <v-tooltip activator="parent">Tools that can be used by all techniques.</v-tooltip>
            </v-fab>
            <v-navigation-drawer v-model="drawer" location="right" width="450" app temporary>
                <ToolDrawer :tool-data="genericTools" />
            </v-navigation-drawer>

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
                    :href="galaxyUrl"
                    class="text-grey-lighten-1 text-caption text-decoration-none"
                    target="_blank"
                >
                    Powered by {{ galaxyAlias }}
                </a>
                <v-spacer />
                <a
                    href="https://www.ornl.gov/"
                    class="text-grey-lighten-1 text-caption text-decoration-none"
                    target="_blank"
                >
                    © {{ new Date().getFullYear() }} ORNL
                </a>
            </v-footer>

            <v-dialog v-model="user.requires_galaxy_login" persistent width="400">
                <v-card class="text-center">
                    <v-card-text>
                        <p class="mb-4">
                            You need to login to {{ galaxyAlias }} to be able to launch tools.
                            Please go to
                            <a target="_blank" :href="galaxyUrl">{{ galaxyUrl }}</a> and log into
                            {{ galaxyAlias }} using your {{ user.login_type }} credentials.
                        </p>
                        <p>
                            If you've already logged in, then you can refresh this page to dismiss
                            this dialog.
                        </p>
                    </v-card-text>
                </v-card>
            </v-dialog>
        </v-main>
    </v-app>
</template>

<script setup>
import Cookies from "js-cookie"
import { computed, onMounted, ref } from "vue"
import { storeToRefs } from "pinia"
import { RouterView, useRoute } from "vue-router"

import ActiveToolsPanel from "@/components/ActiveToolsPanel.vue"
import ToolDrawer from "@/components/ToolDrawer.vue"
import { getTools } from "@/router"
import { useJobStore } from "@/stores/job"
import { useUserStore } from "@/stores/user"
import InfoPanel from "@/components/InfoPanel.vue"
import NotificationPanel from "@/components/NotificationPanel.vue"
import StatusPanel from "@/components/StatusPanel.vue"

const job = useJobStore()
const { running } = storeToRefs(job)
const user = useUserStore()
const { autoopen, given_name, is_admin, is_logged_in, ucams_auth_url, xcams_auth_url } =
    storeToRefs(user)
const route = useRoute()
const drawer = ref(false)
const notificationPanel = ref(null)
const galaxyAlias = import.meta.env.VITE_GALAXY_ALIAS
const galaxyDocsUrl = import.meta.env.VITE_GALAXY_DOCS_URL
const galaxyUrl = import.meta.env.VITE_GALAXY_URL
const novaAlias = import.meta.env.VITE_NOVA_ALIAS
const novaDocsUrl = import.meta.env.VITE_NOVA_DOCS_URL
const novaTutorialUrl = import.meta.env.VITE_NOVA_TUTORIAL_URL

const genericTools = computed(() => {
    const tools = getTools()

    if ("generic-tools" in tools) {
        return tools["generic-tools"]
    }

    return []
})

onMounted(async () => {
    await user.getUser()

    if (user.is_logged_in) {
        await user.userStatus()
    }
})

function toggleDrawer() {
    drawer.value = !drawer.value
}

function logout() {
    Cookies.remove("csrftoken")
    window.location.replace("/logout/")
}
</script>
