import Cookies from "js-cookie"
import { defineStore } from "pinia"

import { useUserStore } from "@/stores/user"

const basePath = import.meta.env.VITE_BASE_PATH
const notificationUrl = `${basePath}api/notification/`

export const useNotificationStore = defineStore("notification", {
    state: () => {
        return {
            display: false,
            message: ""
        }
    },
    actions: {
        async read() {
            try {
                const response = await fetch(notificationUrl)

                if (!response.ok) {
                    throw new Error("Failed to fetch")
                }

                const data = await response.json()

                if (data?.display) {
                    this.display = data.display
                }

                if (data?.message) {
                    this.message = data.message
                }
            } catch (error) {
                console.error("Failed to fetch notification:", error)
            }
        },
        async set() {
            try {
                const user = useUserStore()
                const response = await fetch(notificationUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": Cookies.get("csrftoken")
                    },
                    body: JSON.stringify({
                        api_key: user.apiKey,
                        display: this.display,
                        message: this.message
                    })
                })

                if (!response.ok) {
                    throw new Error("Failed to post notification")
                }
            } catch (err) {
                console.error("Error posting notification:", err)
            }
        }
    }
})
