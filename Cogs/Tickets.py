
    # TODO: make it select which challenge it's for
    @commands.message_command(name="Solution")
    @Logger
    async def mark_solution(
        self, inter: disnake.ApplicationCommandInteraction, message: disnake.Message
    ):
        # Check if channel is in the correct category
        if inter.channel.category_id != 1385339846117294110:
            await inter.response.send_message(
                "This command can only be used in the ticket category", ephemeral=True
            )
            return

        try:
            await Database.add_solution(
                channel_id=inter.channel.id,
                message_id=message.id,
                user_id=message.author.id,
                marked_by=inter.author.id,
            )

            # Create a cleaner message reference
            jump_url = message.jump_url
            await inter.response.send_message(
                f"✅ Marked [this message]({jump_url}) as solution",
                ephemeral=True,
            )

        except Exception as e:
            await inter.response.send_message(
                f"Failed to mark solution: {str(e)}", ephemeral=True
            )

    @commands.slash_command(
        name="solutions",
        description="Get the solutions in this channel",
    )
    @Logger
    async def get_solutions(self, inter: disnake.ApplicationCommandInteraction):
        # Check if channel is in the correct category
        if inter.channel.category_id != 1385339846117294110:
            await inter.response.send_message(
                "This command can only be used in the ticket category", ephemeral=True
            )
            return

        try:
            solutions = await Database.get_solutions(channel_id=inter.channel.id)

            if not solutions:
                await inter.response.send_message(
                    "No solutions have been marked yet", ephemeral=True
                )
                return

            # Format solutions nicely
            messages = []
            for solution in solutions:
                channel = inter.channel
                message = await channel.fetch_message(solution["message_id"])
                if message:
                    message_link = f"https://discord.com/channels/{inter.guild.id}/{channel.id}/{message.id}"
                    messages.append(f"[{message.content}]({message_link})")

            solutions_text = "\n".join(f"• {msg}" for msg in messages)

            await inter.response.send_message(
                f"**Solutions in this channel:**\n{solutions_text}", ephemeral=True
            )

        except Exception as e:
            await inter.response.send_message(
                f"Failed to get solutions: {str(e)}", ephemeral=True
            )
