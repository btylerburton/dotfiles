return {
  "sudormrfbin/cheatsheet.nvim",
  dependencies = {
    "nvim-telescope/telescope.nvim",
    "nvim-lua/plenary.nvim",
    "nvim-lua/popup.nvim",
  },
  cmd = "Cheatsheet",
  keys = {
    {
      "<leader>?",
      "<cmd>Cheatsheet<cr>",
      desc = "Open cheatsheet",
    },
  },
  config = function()
    require("cheatsheet").setup({})
  end,
}
