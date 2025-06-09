<template>
    <v-btn size="x-small" icon>
        <v-icon>mdi-information-outline</v-icon>

        <v-menu activator="parent" :close-on-content-click="false" open-on-hover>
            <v-card width="600">
                <v-card-title class="mb-2 px-0">About This Dashboard</v-card-title>
                <v-card-text class="pa-0">
                    <p class="mb-2">
                        This dashboard has been developed as a part of the NOVA LDRD project. It is
                        meant to serve as a way to launch and manage interactive applications
                        running in
                        <a :href="galaxy_url" target="_blank">Galaxy</a>.
                    </p>

                    <p>
                        The dashboard is currently running version {{ version }}.
                        <a
                            href="https://code.ornl.gov/ndip/nova-dashboard/-/blob/main/CHANGELOG.md"
                            target="_blank"
                        >
                            View Changelog
                        </a>
                    </p>
                </v-card-text>
            </v-card>
        </v-menu>
    </v-btn>
</template>

<script setup>
const galaxy_url = import.meta.env.VITE_GALAXY_URL
const version = import.meta.env.VITE_DASHBOARD_VERSION
</script>
