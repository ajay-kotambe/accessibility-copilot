def run_axe(page):
    try:
        return page.evaluate("""
            () => {
                if (typeof axe === 'undefined') {
                    return {error: 'axe-core not loaded'};
                }
                return axe.run().then(r => {
                    return {
                        violations: r.violations.map(v => ({
                            id: v.id,
                            impact: v.impact,
                            description: v.description,
                            help: v.help,
                            helpUrl: v.helpUrl,
                            tags: v.tags,
                            nodes: v.nodes.map(n => ({
                                html: n.html,
                                target: n.target,
                                impact: n.impact,
                                any: n.any,
                                all: n.all,
                                none: n.none,
                            }))
                        })),
                        incomplete: r.incomplete,
                        passes: r.passes,
                        inapplicable: r.inapplicable,
                    };
                });
            }
        """)
    except Exception as e:
        return {'error': str(e)}
