import { useEffect } from "react"
import { CookMode } from "@/components/CookMode"
import { IndexPage } from "@/components/IndexPage"
import { RecipePage } from "@/components/RecipePage"
import { ShoppingPage } from "@/components/ShoppingPage"
import { config, recipeById } from "@/lib/config"
import { useRoute } from "@/lib/router"

export default function App() {
  const route = useRoute()
  const recipe = route.name === "recipe" || route.name === "cook" ? recipeById.get(route.id) : undefined

  useEffect(() => {
    if (route.name !== "cook") {
      document.title = recipe ? `${recipe.title}: ${config.kitchen}` : route.name === "shopping" ? `Shopping: ${config.kitchen}` : config.kitchen
    }
    if (route.name !== "cook") window.scrollTo({ top: 0 })
  }, [route.name, recipe])

  if (route.name === "cook" && recipe) {
    return (
      <>
        <RecipePage recipe={recipe} />
        <CookMode recipe={recipe} step={route.step} />
      </>
    )
  }
  if (route.name === "recipe" && recipe) return <RecipePage recipe={recipe} />
  if (route.name === "shopping") return <ShoppingPage />
  return <IndexPage />
}
