import { defineStore } from "pinia"

export const useUserStore = defineStore("user", {
    state: () => {
        return {
            autoopen: false, // if true, tools will open in a new tab once they've successfully launched
            given_name: null,
            is_logged_in: false,
            ucams_auth_url: "/",
            xcams_auth_url: "/",
            prompt_login: false,
        }
    },
    actions: {
        async getUser() {
            const response = await fetch("/api/auth/user/")
            const data = await response.json()

            this.given_name = data.given_name
            this.is_logged_in = data.is_logged_in
            this.ucams_auth_url = data.ucams
            this.xcams_auth_url = data.xcams
        },
        async userStatus() {
            const response = await fetch("/api/galaxy/status/");
            const data = await response.json();
            if (data["error"].includes("Please login")) {
                this.prompt_login = true;
            } else {
                this.prompt_login = false;
            }
        },
        userMonitorLogin() {
            setInterval(() => {
                if (this.prompt_login) {
                    this.userStatus();
                } else {
                    return;
                }
            }, 2000)
        },
        getAutoopen() {
            this.autoopen = window.localStorage.getItem("autoopen") === "true"
        },
        toggleAutoopen() {
            this.autoopen = !this.autoopen
            window.localStorage.setItem("autoopen", this.autoopen)
        },
        resetUser() {
            this.autoopen = false
            this.given_name = null
            this.is_logged_in = false
            this.ucams_auth_url = "/"
            this.xcams_auth_url = "/"
            this.prompt_login = false
        },
    }
})
