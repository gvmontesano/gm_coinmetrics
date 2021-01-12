var express = require('express');
var router = express.Router();

const recipes_db = require("../recipes.json");
const alternatives_db = require("../alternatives.json");

/* GET home page. */
router.get('/', function (req, res, next) {
  res.render('index', { title: 'Ethical Eats' });
});

router.get("/recipes", function (req, res) {
  res.render("recipes", {
    title: "Ethical Eats",
    recipes: recipes_db.recipe_cards
  });
});

router.get("/create_recipe", function (req, res) {
  res.render("create_recipe", {
    title: "Ethical Eats",
  });
});

router.get("/recipe_card", function (req, res) {
  const recipe = recipes_db.recipe_cards.find(p => p.id == req.query.id);
  res.render("recipe_card", {
    title: `Recipe: ${recipe.name}`,
    recipe,
    alternatives: alternatives_db.alternatives
  });
});

module.exports = router;
