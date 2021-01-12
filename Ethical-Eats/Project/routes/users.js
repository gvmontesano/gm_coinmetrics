var express = require('express');
var secured = require('../lib/middleware/secured');
var router = express.Router();

const recipes_db = require("../recipes.json");
const alternatives_db = require("../alternatives.json");

/* GET user profile. */
router.get('/user', secured(), function (req, res, next) {
  const { _raw, _json, ...userProfile } = req.user;
  res.render('user', {
    userProfile: JSON.stringify(userProfile, null, 2),
    title: 'Profile page'
  });
});

router.get("/recipes", function (req, res) {
  const { _raw, _json, ...userProfile } = req.user;
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
  const { _raw, _json, ...userProfile } = req.user;
  res.render("recipe_card", {
    title: `Recipe: ${recipe.name}`,
    recipe,
    alternatives: alternatives_db.alternatives
  });
});

module.exports = router;
